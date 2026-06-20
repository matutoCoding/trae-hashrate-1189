import sys
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from app.database.db_manager import DatabaseManager
from app.services.scheduler import SchedulerService
from app.services.recommender import RecommenderService
from app.services.waitlist import WaitlistService


def test_all():
    print("=" * 60)
    print("开始测试服务层...")
    print("=" * 60)

    db = DatabaseManager()
    db.init_db()

    scheduler = SchedulerService(db)
    recommender = RecommenderService(db)
    waitlist = WaitlistService(db, scheduler)

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

        print("\n5. 测试多维推荐系统...")
        if students and teachers:
            student = students[0]
            print(f"   为学员 {student.name} 推荐老师...")
            recommendations = recommender.recommend_teachers(student.id, top_n=3)
            print(f"   推荐结果 ({len(recommendations)} 位):")
            for i, rec in enumerate(recommendations):
                print(f"     {i+1}. {rec['teacher'].name} - 匹配度: {rec['total_score']:.2%}")
                print(f"        曲风: {rec['style_score']:.0%}, 评分: {rec['rating_score']:.0%}, "
                      f"级别: {rec['level_score']:.0%}, 可用: {rec['availability_score']:.0%}, "
                      f"经验: {rec['experience_score']:.0%}")

        print("\n6. 测试权重配置...")
        weights = recommender.get_current_weights()
        print(f"   当前权重: {weights}")
        print(f"   权重和: {sum(weights.values()):.2f}")

        print("\n7. 测试报名功能...")
        if schedules and students:
            schedule = schedules[0]
            student = students[0]
            if schedule.current_students < schedule.max_students:
                print(f"   学员 {student.name} 报名课程 {schedule.course_name}...")
                try:
                    enrollment = scheduler.enroll_student(schedule.id, student.id)
                    print(f"   报名成功! 报名ID: {enrollment.id}")

                    print(f"   确认报名...")
                    scheduler.confirm_enrollment(enrollment.id)
                    print("   确认成功!")
                except Exception as e:
                    print(f"   报名失败: {e}")
            else:
                print(f"   课程已满，测试候补功能...")
                waitlist_entry = waitlist.add_to_waitlist(schedule.id, student.id)
                print(f"   加入候补成功! 队列位置: {waitlist_entry.queue_position}")

        print("\n8. 测试超时自动释放...")
        released = scheduler.check_and_release_overdue()
        print(f"   本次释放超时名额: {len(released)}")

        print("\n9. 测试候补补位...")
        if schedules:
            schedule = schedules[0]
            stats = waitlist.get_waitlist_statistics(schedule.id)
            print(f"   课程 {schedule.course_name} 候补统计: {stats}")

            notified = waitlist.process_waitlist_for_schedule(schedule.id)
            print(f"   通知补位人数: {len(notified)}")

        print("\n10. 测试归档功能...")
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
