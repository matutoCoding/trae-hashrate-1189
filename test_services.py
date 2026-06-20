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

        print("\n11. 测试归档功能...")
        archived = scheduler.archive_completed_courses()
        print(f"    本次归档课程数: {archived}")

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
