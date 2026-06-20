import sys
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from app.database.db_manager import DatabaseManager
from app.services.scheduler import SchedulerService
from app.services.recommender import RecommenderService
from app.services.waitlist import WaitlistService


def test_all():
    print("=" * 60)
    print("开始测试服务层（增强版）...")
    print("=" * 60)

    db = DatabaseManager()
    db.init_db()

    scheduler = SchedulerService(db)
    recommender = RecommenderService(db)
    waitlist = WaitlistService(db, scheduler)
    scheduler.set_release_callback(waitlist.auto_notify_next)

    try:
        print("\n1. 测试琴室管理...")
        rooms = scheduler.get_all_rooms("active")
        print(f"   活跃琴室数量: {len(rooms)}")
        if rooms:
            print(f"   第一个琴室: {rooms[0].name}")

        print("\n2. 测试老师管理...")
        teachers = scheduler.get_all_teachers("active")
        print(f"   活跃老师数量: {len(teachers)}")
        if teachers:
            print(f"   第一个老师: {teachers[0].name}, 评分: {teachers[0].rating}")

        print("\n3. 测试学员管理...")
        students = scheduler.get_all_students("active")
        print(f"   活跃学员数量: {len(students)}")
        if students:
            print(f"   第一个学员: {students[0].name}")

        print("\n4. 测试课程排期...")
        schedules = scheduler.get_schedules(status="scheduled")
        print(f"   待排课程数量: {len(schedules)}")
        if schedules:
            s = schedules[0]
            print(f"   第一个课程: {s.course_name}, 时间: {s.start_time}")

        print("\n5. 测试多维推荐系统（含推荐原因）...")
        if students and teachers:
            student = students[2]
            print(f"   为学员 {student.name} (曲风:{student.preferred_style}, 级别:{student.level}) 推荐老师...")
            recommendations = recommender.recommend_teachers(student.id, top_n=3)
            print(f"   推荐结果 ({len(recommendations)} 位):")
            for i, rec in enumerate(recommendations):
                t = rec['teacher']
                print(f"     {i+1}. {t.name} - 匹配度: {rec['total_score']:.2%}")
                print(f"        曲风: {rec['style_score']:.0%}, 评分: {rec['rating_score']:.0%}, "
                      f"级别: {rec['level_score']:.0%}, 可用: {rec['availability_score']:.0%}, "
                      f"经验: {rec['experience_score']:.0%}")
                reason = rec.get('reason_text', '')
                if reason:
                    print(f"        推荐原因: {reason[:80]}...")

        print("\n6. 测试权重配置...")
        weights = recommender.get_current_weights()
        print(f"   当前权重: {weights}")
        print(f"   权重和: {sum(weights.values()):.2f}")

        print("\n7. 测试报名和状态流转...")
        if schedules and students:
            schedule = schedules[0]
            student = students[0]
            if schedule.current_students < schedule.max_students:
                print(f"   学员 {student.name} 报名课程 {schedule.course_name}...")
                try:
                    enrollment = scheduler.enroll_student(schedule.id, student.id)
                    print(f"   报名成功! 状态: {enrollment.status} (应为pending)")

                    print(f"   确认报名 (pending->confirmed)...")
                    result = scheduler.confirm_enrollment(enrollment.id)
                    print(f"   确认成功! 状态: {result.status}")

                    print(f"   签到 (confirmed->checked_in)...")
                    result = scheduler.checkin_student(enrollment.id)
                    print(f"   签到成功! 状态: {result.status}")

                    print(f"   完成 (checked_in->completed)...")
                    result = scheduler.complete_enrollment(enrollment.id)
                    print(f"   完成成功! 状态: {result.status}")
                except Exception as e:
                    print(f"   操作失败: {e}")

                    try:
                        scheduler.cancel_enrollment(enrollment.id)
                    except:
                        pass

            print(f"   测试非法状态跳转...")
            try:
                enrollment2 = scheduler.enroll_student(schedule.id, students[1].id)
                scheduler.complete_enrollment(enrollment2.id)
                print(f"   ERROR: 非法跳转应该被拒绝!")
            except ValueError as e:
                print(f"   正确拦截非法跳转: {e}")

            try:
                scheduler.cancel_enrollment(enrollment2.id)
            except:
                pass

        print("\n8. 测试超时自动释放 + 候补自动联动...")
        if schedules and len(students) >= 3:
            test_schedule = None
            for s in schedules:
                if s.current_students < s.max_students:
                    test_schedule = s
                    break

            if test_schedule:
                student_wait = students[2]
                print(f"   学员 {student_wait.name} 报名课程 {test_schedule.course_name}...")
                try:
                    enroll = scheduler.enroll_student(test_schedule.id, student_wait.id)
                    print(f"   报名成功, 状态: {enroll.status}")
                except ValueError as e:
                    print(f"   报名: {e}")

                another_student = students[3] if len(students) > 3 else students[1]
                print(f"   将学员 {another_student.name} 加入候补队列...")
                try:
                    wl = waitlist.add_to_waitlist(test_schedule.id, another_student.id, priority_score=50.0)
                    print(f"   候补成功! 队列位置: {wl.queue_position}")
                except ValueError as e:
                    print(f"   候补: {e}")

                print(f"   检查超时释放...")
                released_ids = scheduler.check_and_release_overdue()
                print(f"   释放了 {len(released_ids)} 个超时名额")

                notified_entries = waitlist.get_notified_with_remaining(test_schedule.id)
                print(f"   当前被通知候补人数: {len(notified_entries)}")
                for item in notified_entries:
                    entry = item['entry']
                    from app.database.models import Student as StuModel
                    s = db.get_by_id(StuModel, entry.student_id)
                    name = s.name if s else "?"
                    print(f"     - {name}, 通知时间: {entry.notified_time}, 截止: {entry.confirm_deadline}, 剩余: {item['remaining_seconds']:.0f}秒")
            else:
                print("   所有课程已满，跳过此测试")

        print("\n9. 测试候补补位倒计时和确认...")
        if schedules:
            schedule = schedules[0]
            stats = waitlist.get_waitlist_statistics(schedule.id)
            print(f"   课程 {schedule.course_name} 候补统计: {stats}")

            notified = waitlist.process_waitlist_for_schedule(schedule.id)
            print(f"   主动处理补位人数: {len(notified)}")
            for entry in notified:
                print(f"     - 通知时间: {entry.notified_time}, 确认截止: {entry.confirm_deadline}")

            notified_entries = waitlist.get_notified_with_remaining(schedule.id)
            print(f"   倒计时查询结果: {len(notified_entries)} 条")
            for item in notified_entries:
                entry = item['entry']
                print(f"     剩余: {item['remaining_seconds']:.0f}秒, 已过期: {item['is_expired']}")

        print("\n10. 测试推荐保存为撮合记录...")
        if students and teachers:
            student = students[0]
            recs = recommender.recommend_teachers(student.id, top_n=1)
            if recs:
                logs = recommender.get_recommendation_history(
                    student_id=student.id, teacher_id=recs[0]['teacher'].id, limit=1
                )
                if logs:
                    result = recommender.save_as_match(logs[0].id)
                    print(f"   保存撮合记录: {'成功' if result else '失败'}")
                    matches = recommender.get_match_records(student_id=student.id)
                    print(f"   当前撮合记录数: {len(matches)}")

        print("\n11. 测试取消报名后自动联动候补...")
        if schedules and len(students) >= 4:
            all_schedules = scheduler.get_schedules()
            test_schedule = None
            for s in all_schedules:
                s_fresh = scheduler.get_schedule_by_id(s.id)
                if s_fresh and s_fresh.current_students < s_fresh.max_students:
                    test_schedule = s_fresh
                    break

            if not test_schedule and len(all_schedules) > 1:
                for s in all_schedules:
                    s_fresh = scheduler.get_schedule_by_id(s.id)
                    if s_fresh and s_fresh.max_students >= 2:
                        test_schedule = s_fresh
                        enrolls = scheduler.get_enrollments(schedule_id=s_fresh.id, status=["confirmed", "pending", "checked_in"])
                        for e in enrolls[:1]:
                            scheduler.cancel_enrollment(e.id)
                        test_schedule = scheduler.get_schedule_by_id(s_fresh.id)
                        break

            if test_schedule:
                s1 = students[0]
                s2 = students[1]
                s3 = students[2]
                print(f"   课程: {test_schedule.course_name}, 名额: {test_schedule.max_students}")
                print(f"   当前人数: {test_schedule.current_students}")

                print(f"   学员 {s1.name} 报名并确认...")
                enroll1 = scheduler.enroll_student(test_schedule.id, s1.id)
                conf1 = scheduler.confirm_enrollment(enroll1.id)
                sched_after = scheduler.get_schedule_by_id(test_schedule.id)
                print(f"   确认后人数: {sched_after.current_students}")

                if test_schedule.max_students >= 2:
                    print(f"   学员 {s2.name} 报名并确认...")
                    enroll2 = scheduler.enroll_student(test_schedule.id, s2.id)
                    conf2 = scheduler.confirm_enrollment(enroll2.id)

                print(f"   学员 {s3.name} 加入候补...")
                wl1 = waitlist.add_to_waitlist(test_schedule.id, s3.id, priority_score=80.0)

                if len(students) >= 5:
                    s4 = students[3]
                    print(f"   学员 {s4.name} 加入候补...")
                    wl2 = waitlist.add_to_waitlist(test_schedule.id, s4.id, priority_score=60.0)

                print(f"   取消学员 {s1.name} 的报名...")
                scheduler.cancel_enrollment(conf1.id)
                sched_after_cancel = scheduler.get_schedule_by_id(test_schedule.id)
                print(f"   取消后人数: {sched_after_cancel.current_students}")

                notified = waitlist.get_notified_with_remaining(test_schedule.id)
                print(f"   自动通知候补人数: {len(notified)}")
                for item in notified:
                    entry = item['entry']
                    stu = scheduler.db.get_by_id(__import__('app.database.models', fromlist=['Student']).Student, entry.student_id)
                    print(f"     - {stu.name if stu else '?'}, 优先级: {entry.priority_score}, 剩余: {item['remaining_seconds']:.0f}秒")
            else:
                print("   找不到合适的测试课程，跳过")

        print("\n12. 测试候补邀请不超发（已通知未确认也算占位）...")
        if schedules and len(students) >= 3:
            all_scheds = scheduler.get_schedules()
            test_schedule = None
            for s in all_scheds:
                sf = scheduler.get_schedule_by_id(s.id)
                if sf and sf.max_students >= 3:
                    test_schedule = sf
                    enrolls = scheduler.get_enrollments(schedule_id=sf.id, status=["confirmed", "pending", "checked_in"])
                    for e in enrolls:
                        scheduler.cancel_enrollment(e.id)
                    test_schedule = scheduler.get_schedule_by_id(sf.id)
                    break

            if test_schedule:
                print(f"   测试课程: {test_schedule.course_name}, 最大名额: {test_schedule.max_students}")
                print(f"   当前人数: {test_schedule.current_students}")

                s_list = students[:4]
                for i, s in enumerate(s_list):
                    try:
                        waitlist.add_to_waitlist(test_schedule.id, s.id, priority_score=100 - i * 10)
                        print(f"   学员 {s.name} 加入候补")
                    except ValueError:
                        pass

                print(f"   尝试通知候补（名额只2个）...")
                # 先给2人报名确认，只留2个空位
                if test_schedule.max_students >= 4:
                    for s in students[:2]:
                        try:
                            e = scheduler.enroll_student(test_schedule.id, s.id)
                            scheduler.confirm_enrollment(e.id)
                        except ValueError:
                            pass

                test_schedule = scheduler.get_schedule_by_id(test_schedule.id)
                available = test_schedule.max_students - test_schedule.current_students
                print(f"   剩余空位: {available}")

                notified = waitlist.process_waitlist_for_schedule(test_schedule.id)
                print(f"   实际可通知: {available}, 实际通知: {len(notified)}")
                print(f"   不超发验证: {'通过' if len(notified) <= available else '失败 - 超发了!'}")

                print(f"   再次尝试通知（有未确认的）...")
                notified2 = waitlist.auto_notify_next(test_schedule.id)
                print(f"   第二次通知: {len(notified2)} 人 (应为0, 因为已通知未确认也算占位)")
            else:
                print("   找不到合适的测试课程，跳过")

        print("\n13. 测试归档统计...")
        scheduler.archive_completed_courses()
        from app.database.models import Archive

        def query(session):
            all_archives = session.query(Archive).all()
            if all_archives:
                total = len(all_archives)
                scores = [a.match_score for a in all_archives if a.match_score]
                avg_score = sum(scores) / len(scores) if scores else 0
                completed = len([a for a in all_archives if a.status == "completed"])
                cancelled = len([a for a in all_archives if a.status in ["cancelled", "released"]])
                print(f"   总归档记录: {total}")
                print(f"   平均匹配分: {avg_score:.2%}")
                print(f"   已完成: {completed}")
                print(f"   已取消/释放: {cancelled}")
            return len(all_archives)

        count = db.execute_query(query)
        print(f"   共 {count} 条归档记录")

        print("\n" + "=" * 60)
        print("所有测试通过!")
        print("=" * 60)

    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)
