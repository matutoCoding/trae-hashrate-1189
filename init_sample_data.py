from datetime import datetime, timedelta
from app.database.db_manager import DatabaseManager
from app.services.scheduler import SchedulerService
from app.services.recommender import RecommenderService
from app.services.waitlist import WaitlistService


def init_sample_data():
    db = DatabaseManager()
    db.init_db()

    scheduler = SchedulerService(db)
    recommender = RecommenderService(db)
    waitlist = WaitlistService(db, scheduler)

    print("开始初始化示例数据...")

    if not scheduler.get_all_rooms():
        print("添加琴室...")
        scheduler.add_room("琴室A", "一楼101", 1, "古筝2台,钢琴1台", "active")
        scheduler.add_room("琴室B", "一楼102", 1, "古筝2台", "active")
        scheduler.add_room("琴室C", "二楼201", 4, "古筝5台,音响设备", "active")
        scheduler.add_room("集体课室", "二楼202", 10, "古筝10台,投影设备", "active")

    if not scheduler.get_all_teachers():
        print("添加老师...")
        scheduler.add_teacher(
            "李老师", "13800138001", "女", 35, "高级",
            "传统,现代", 4.9, 10, "中央音乐学院古筝专业",
            "擅长传统曲目教学，教学经验丰富", "active"
        )
        scheduler.add_teacher(
            "王老师", "13800138002", "男", 28, "中级",
            "流行,现代", 4.7, 5, "上海音乐学院硕士",
            "擅长流行编曲和即兴演奏", "active"
        )
        scheduler.add_teacher(
            "张老师", "13800138003", "女", 42, "专业",
            "传统,古典", 5.0, 15, "中国音乐学院教授",
            "国家一级演奏员，考级评委", "active"
        )
        scheduler.add_teacher(
            "陈老师", "13800138004", "女", 25, "初级",
            "流行,民间", 4.5, 3, "中央音乐学院本科",
            "亲和力强，擅长儿童教学", "active"
        )

    if not scheduler.get_all_students():
        print("添加学员...")
        scheduler.add_student(
            "小明", "13900139001", "男", 8, "入门",
            "流行", "兴趣爱好", "一级", "active"
        )
        scheduler.add_student(
            "小红", "13900139002", "女", 12, "初级",
            "传统", "考级", "三级", "active"
        )
        scheduler.add_student(
            "小华", "13900139003", "女", 25, "中级",
            "现代,流行", "兴趣爱好", "六级", "active"
        )
        scheduler.add_student(
            "小李", "13900139004", "男", 30, "高级",
            "传统,古典", "专业发展", "九级", "active"
        )
        scheduler.add_student(
            "小芳", "13900139005", "女", 10, "入门",
            "传统", "考级", "一级", "active"
        )

    if not scheduler.get_all_music_pieces():
        print("添加考级曲目...")
        pieces = [
            ("渔舟唱晚", "娄树华", "传统", "中级", "中央音乐学院", "五级", 5, "经典传统曲目"),
            ("高山流水", "传统", "传统", "高级", "中央音乐学院", "七级", 6, "浙派代表曲目"),
            ("战台风", "王昌元", "现代", "中级", "中国音乐学院", "六级", 4, "现代经典作品"),
            ("井冈山上太阳红", "赵曼琴", "现代", "高级", "中央音乐学院", "八级", 3, "快速指序代表作"),
            ("林冲夜奔", "陆修棠", "现代", "专业", "上海音乐学院", "十级", 7, "叙事性大型作品"),
            ("春江花月夜", "传统", "传统", "初级", "中国音乐学院", "三级", 4, "入门经典曲目"),
            ("挤牛奶", "张燕", "民间", "入门", "中央音乐学院", "一级", 2, "考级一级曲目"),
            ("凤翔歌", "传统", "传统", "入门", "中国音乐家协会", "二级", 2, "考级二级曲目"),
        ]
        for name, composer, style, diff, exam_cat, exam_level, duration, desc in pieces:
            scheduler.add_music_piece(
                name, composer, style, diff, exam_cat, exam_level, duration, desc
            )

    if not scheduler.get_schedules():
        print("添加课程排期...")
        now = datetime.now()
        rooms = scheduler.get_all_rooms("active")
        teachers = scheduler.get_all_teachers("active")

        for i in range(5):
            start_time = now + timedelta(days=i+1, hours=9)
            end_time = start_time + timedelta(hours=1)

            scheduler.add_schedule(
                rooms[i % len(rooms)].id,
                teachers[i % len(teachers)].id,
                f"古筝一对一课程-{i+1}",
                "一对一",
                start_time,
                end_time,
                1,
                f"第{i+1}节课"
            )

        start_time = now + timedelta(days=1, hours=14)
        end_time = start_time + timedelta(hours=2)
        scheduler.add_schedule(
            rooms[2].id,
            teachers[2].id,
            "古筝小组课",
            "小组课",
            start_time,
            end_time,
            4,
            "零基础小组课"
        )

    print("示例数据初始化完成！")


if __name__ == "__main__":
    init_sample_data()
