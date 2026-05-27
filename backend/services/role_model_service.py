import json
from sqlalchemy.orm import Session
from backend.models import RoleModel, RoleModelQuality, Quality, QualityLevel, CategoryMapping

# ── 默认5级阶梯 ──
DEFAULT_LEVELS = [
    (1, "萌芽期", "刚刚开始，需要刻意提醒自己", 0),
    (2, "习惯期", "已经形成初步习惯，不再需要强烈意志力", 100),
    (3, "内化期", "行为已融入日常，自然而然地做到", 300),
    (4, "精通期", "不仅自己能做好，还能影响他人", 600),
    (5, "无意识期", "已成为你的身份标签，别人因这点记住你", 1000),
]

# ── 种子数据（12位明星 + 16项品质 + 48条推荐活动）──
SEED_ROLE_MODELS = [
    {
        "name": "沈腾",
        "field": "演员 / 喜剧人",
        "avatar": "theater",
        "image_url": "/api/v1/static/images/role_models/shenteng.png",
        "description": "开心麻花演员，以高情商和真诚幽默著称。用自嘲化解尴尬、用细节温暖他人。",
        "qualities": [
            {
                "quality_name": "高情商",
                "description": "沈腾的高情商不是滴水不漏的圆滑，而是一种带着烟火气的真诚——犯错不甩锅、尴尬用幽默化解、下意识关注身边人的需求。",
                "suggested_activities": [
                    {"content": "情绪日记：记录今天一次情绪波动及你的应对方式", "category": "生活", "duration_minutes": 10, "frequency": "每日", "reason": "提升自我觉察，是情商的基础"},
                    {"content": "社交观察：在公共场合主动帮助一位陌生人（让座、扶门等）", "category": "生活", "duration_minutes": 5, "frequency": "每日", "reason": "培养关注他人需求的习惯"},
                    {"content": "自嘲练习：遇到尴尬时试着用幽默化解，事后记录效果", "category": "生活", "duration_minutes": 5, "frequency": "遇到时", "reason": "沈腾的核心情商技巧"},
                ],
            },
        ],
    },
    {
        "name": "马天宇",
        "field": "演员 / 歌手",
        "avatar": "heart",
        "image_url": "/api/v1/static/images/role_models/matianyu.png",
        "description": "娱乐圈公认的「无差评明星」，待人诚恳温暖，细节处见人品。",
        "qualities": [
            {
                "quality_name": "待人诚恳",
                "description": "马天宇经历过坎坷童年，却把苦难变成了对他人的温柔。高铁让座、帮同事挡风、原谅抛弃自己的父亲——他用行动诠释了「自己淋过雨，所以想给别人打伞」。",
                "suggested_activities": [
                    {"content": "每周联系一位久未联系的朋友或家人，真诚问候", "category": "生活", "duration_minutes": 15, "frequency": "每周", "reason": "诚恳待人从维系关系开始"},
                    {"content": "写感恩日记：记录今天谁帮助了你，你帮助了谁", "category": "生活", "duration_minutes": 10, "frequency": "每日", "reason": "培养感恩之心"},
                    {"content": "匿名做一件好事（捐款、帮同事分担工作等）", "category": "生活", "duration_minutes": 15, "frequency": "每周", "reason": "不求回报的善意最真诚"},
                ],
            },
        ],
    },
    {
        "name": "王安宇",
        "field": "演员",
        "avatar": "smile",
        "image_url": "/api/v1/static/images/role_models/wanganyu.png",
        "description": "中国传媒大学学霸，高考614分，从流量偶像成功转型实力派演员。落落大方、谦和有礼。",
        "qualities": [
            {
                "quality_name": "落落大方",
                "description": "王安宇在白玉兰奖主持时台风稳健、毫不怯场；双手接话筒、弯腰迁就合影路人——教养刻进细节。他相信「当实力成为底气，知识就是最硬的通行证」。",
                "suggested_activities": [
                    {"content": "朗读练习：每天朗读一段文章（新闻/诗词/演讲稿），录音回听改进", "category": "学习", "duration_minutes": 15, "frequency": "每日", "reason": "提升口头表达能力和台风"},
                    {"content": "知识积累：每天学习一项新知识并做笔记", "category": "学习", "duration_minutes": 30, "frequency": "每日", "reason": "知识是自信的底气"},
                    {"content": "社交练习：每天主动与一位不熟悉的人进行简短交流", "category": "生活", "duration_minutes": 10, "frequency": "每日", "reason": "克服社交恐惧，培养大方气质"},
                    {"content": "礼仪自检：每次与人交流后回顾自己的言行举止是否得体", "category": "生活", "duration_minutes": 5, "frequency": "每日", "reason": "教养藏在细节里"},
                ],
            },
        ],
    },
    {
        "name": "陈瑶",
        "field": "演员",
        "avatar": "star",
        "image_url": "/api/v1/static/images/role_models/chenyao.png",
        "description": "从《无心法师》岳绮罗到《乘风2026》，用自律和坚韧证明自己的实力派演员。",
        "qualities": [
            {
                "quality_name": "自律坚持",
                "description": "陈瑶零唱跳基础，10天高强度集训完成全开麦舞台，日均训练12小时。她相信「凡事预则立，不预则废」，坚持每日/每周计划。",
                "suggested_activities": [
                    {"content": "制定明日计划：按重要性和紧急性排列待办事项", "category": "工作", "duration_minutes": 10, "frequency": "每日", "reason": "计划是自律的第一步"},
                    {"content": "固定时间锻炼身体（跑步/健身/瑜伽等）", "category": "运动", "duration_minutes": 30, "frequency": "每日", "reason": "身体自律带动精神自律"},
                    {"content": "专注训练：每天设定一段无干扰的深度工作时间", "category": "工作", "duration_minutes": 60, "frequency": "每日", "reason": "培养专注力和执行力"},
                ],
            },
            {
                "quality_name": "真诚自信",
                "description": "陈瑶不按工业化完美套路来，敢于暴露不足——初舞台坦言「四肢不灵活、排练忘词」。她相信「真实比完美更重要」，最终以真诚赢得观众的喜爱。",
                "suggested_activities": [
                    {"content": "坦诚日记：写下今天一个你本想掩饰的不足，思考如何改进", "category": "生活", "duration_minutes": 10, "frequency": "每日", "reason": "接纳不完美是自信的开始"},
                    {"content": "公开表达：在社交平台或小范围分享一次真实想法", "category": "生活", "duration_minutes": 10, "frequency": "每周", "reason": "练习真实表达，降低伪装成本"},
                ],
            },
        ],
    },
    {
        "name": "黄灿灿",
        "field": "演员",
        "avatar": "sun",
        "image_url": "/api/v1/static/images/role_models/huangcancan.png",
        "description": "武大樱花女神，以「活人感」和真实不做作出圈。不删旧帖、不避旧事、坦然做自己。",
        "qualities": [
            {
                "quality_name": "真实做自己",
                "description": "黄灿灿是娱乐圈少有的「活人」——社交平台像朋友圈一样随意、综艺敢素颜出镜、坦承「恋爱脑」毫不避讳。她用真实感证明：不完美才是最大的魅力。",
                "suggested_activities": [
                    {"content": "真实记录：写一篇不加修饰的日记，记录今天最真实的感受", "category": "生活", "duration_minutes": 10, "frequency": "每日", "reason": "练习面对真实的自己"},
                    {"content": "拒绝清单：今天对一件你不想做的事说「不」", "category": "生活", "duration_minutes": 5, "frequency": "每日", "reason": "停止迎合他人"},
                    {"content": "素颜出行：不化妆或穿最舒服的衣服出门一次", "category": "生活", "duration_minutes": 0, "frequency": "每周", "reason": "卸下面具，习惯被人看到真实的自己"},
                ],
            },
        ],
    },
    {
        "name": "易烊千玺",
        "field": "演员 / 歌手 / 舞者",
        "avatar": "award",
        "image_url": "/api/v1/static/images/role_models/yiyangqianxi.png",
        "description": "最年轻金鸡影帝，00后首位200亿票房男演员。在最巅峰时主动按下暂停键，清醒而克制。",
        "qualities": [
            {
                "quality_name": "清醒自省",
                "description": "易烊千玺12年从偶像到影帝，却在最巅峰时因疲惫主动推掉拍戏计划休息调整。他不被惯性裹挟，始终保持着对自我的清醒审视。",
                "suggested_activities": [
                    {"content": "每周复盘：回顾本周得失，写下3件做得好的和3件需要改进的", "category": "工作", "duration_minutes": 20, "frequency": "每周", "reason": "定期自省是保持清醒的关键"},
                    {"content": "深度阅读：每天读一本好书30分钟并写简短感悟", "category": "阅读", "duration_minutes": 30, "frequency": "每日", "reason": "阅读使人沉静和清醒"},
                ],
            },
        ],
    },
    {
        "name": "游本昌",
        "field": "演员 / 艺术家",
        "avatar": "flame",
        "image_url": "/api/v1/static/images/role_models/youbenchang.png",
        "description": "92岁高龄仍活跃在艺术一线。跑龙套30年不言弃，78岁卖房排话剧，90岁演《繁花》惊艳全国。",
        "qualities": [
            {
                "quality_name": "终身热爱",
                "description": "游本昌52岁才等到第一个主角「济公」，78岁卖掉唯一住房排演《弘一法师》，82岁骨折术后25天绑绷带登台。他用一生诠释了对艺术的赤诚热爱。",
                "suggested_activities": [
                    {"content": "学习一项新技能（乐器/绘画/编程等），每天坚持练习", "category": "学习", "duration_minutes": 30, "frequency": "每日", "reason": "终身学习是终身热爱的前提"},
                    {"content": "阅读名人传记或纪录片，了解他人如何坚持热爱", "category": "阅读", "duration_minutes": 20, "frequency": "每周", "reason": "从榜样身上汲取力量"},
                ],
            },
        ],
    },
    {
        "name": "辛芷蕾",
        "field": "演员",
        "avatar": "rocket",
        "image_url": "/api/v1/static/images/role_models/xinzhilei.png",
        "description": "从黑龙江鹤岗走到威尼斯影后，花了二十年。非科班出身，靠拼命努力把「白日梦」变成现实。",
        "qualities": [
            {
                "quality_name": "大胆追梦",
                "description": "辛芷蕾从不讳言「想红」的野心，用二十年将看似不可能的梦想一一实现——威尼斯影后、话剧112页台词一人饰22角。她的故事证明：大胆做梦，更要拼命实现。",
                "suggested_activities": [
                    {"content": "写下你的年度目标，拆解为月度里程碑", "category": "工作", "duration_minutes": 30, "frequency": "每月", "reason": "把梦想变成可执行的计划"},
                    {"content": "每天做一件超出舒适区的事", "category": "工作", "duration_minutes": 15, "frequency": "每日", "reason": "梦想要靠行动而非空想"},
                ],
            },
        ],
    },
    {
        "name": "全红婵",
        "field": "运动员 / 奥运冠军",
        "avatar": "heart",
        "image_url": "/api/v1/static/images/role_models/quanhongchan.png",
        "description": "从农村走出的奥运跳水冠军。带着伤病征战，却将直播收入悉数捐给乡村儿童。",
        "qualities": [
            {
                "quality_name": "温柔善良",
                "description": "全红婵面对比赛失误没有陷入「自证陷阱」，以温柔化解分歧。她将赛后直播收入全部捐给乡村儿童，重新定义了什么是真正的强大。",
                "suggested_activities": [
                    {"content": "每天对身边的人说一句真诚的赞美或感谢", "category": "生活", "duration_minutes": 5, "frequency": "每日", "reason": "温柔从表达善意开始"},
                    {"content": "每月参与一次公益活动（捐款、志愿者等）", "category": "生活", "duration_minutes": 60, "frequency": "每月", "reason": "把善意转化为行动"},
                ],
            },
        ],
    },
    {
        "name": "刘宇宁",
        "field": "演员 / 歌手",
        "avatar": "user",
        "image_url": "/api/v1/static/images/role_models/liuyuning.png",
        "description": "从直播间走出的非科班演员，坚持提前背熟所有台词，骨折状态下仍自己完成所有打戏。",
        "qualities": [
            {
                "quality_name": "踏实敬业",
                "description": "刘宇宁拍戏从不看手机不拿剧本，坚持提前背熟所有台词。骨折受伤仍自己完成打戏，从未耽误拍摄。他坦言：「作为演员，作品才是立身之本。」",
                "suggested_activities": [
                    {"content": "今日事今日毕：完成今天计划的所有任务，不拖延", "category": "工作", "duration_minutes": 0, "frequency": "每日", "reason": "敬业从完成承诺开始"},
                    {"content": "精益求精：选择一项日常任务，今天比昨天做得更好一点", "category": "工作", "duration_minutes": 20, "frequency": "每日", "reason": "用更高的标准要求自己"},
                ],
            },
        ],
    },
    {
        "name": "曹骏",
        "field": "演员",
        "avatar": "shield",
        "image_url": "/api/v1/static/images/role_models/caojun.png",
        "description": "童星出道后经历漫长低谷，在《演员请就位2》市场评级倒数第一，却用真诚打动所有人。",
        "qualities": [
            {
                "quality_name": "坚韧不拔",
                "description": "曹骏从巅峰跌入谷底，市场评级倒数第一时真诚发问「我到底还适不适合做演员」。他没有放弃，为角色去山区体验生活、学方言、研究动物形态，最终凭《无忧渡》再度翻红。",
                "suggested_activities": [
                    {"content": "面对困难：完成一件你一直逃避的任务", "category": "工作", "duration_minutes": 30, "frequency": "每周", "reason": "直面困难是坚韧的第一步"},
                    {"content": "坚持运动：即使不想动，也坚持完成今天的最低运动量", "category": "运动", "duration_minutes": 20, "frequency": "每日", "reason": "身体坚持带动精神坚持"},
                ],
            },
        ],
    },
    {
        "name": "舒淇",
        "field": "演员 / 导演",
        "avatar": "sun",
        "image_url": "/api/v1/static/images/role_models/shuqi.png",
        "description": "入行30年，从争议中走出，坦然面对过去。2025年执导长片获釜山最佳导演奖。",
        "qualities": [
            {
                "quality_name": "自我和解",
                "description": "舒淇不后悔不辩解过往，用作品重新定义自我。社交平台晒雀斑素颜和皱纹——她活出了「美而不自知」的境界，与自己的所有不完美和解。",
                "suggested_activities": [
                    {"content": "冥想练习：每天冥想10分钟，观察但不评判自己的想法", "category": "冥想", "duration_minutes": 10, "frequency": "每日", "reason": "冥想是自我接纳的捷径"},
                    {"content": "自我对话：写下让你感到不安的一件事，然后以好朋友的口吻给自己写一封回信", "category": "生活", "duration_minutes": 15, "frequency": "每周", "reason": "学会与自己和解"},
                ],
            },
        ],
    },
]


def seed_role_models(db: Session):
    """检查并初始化种子数据（幂等操作，仅在没有 RoleModel 数据时执行）"""
    existing = db.query(RoleModel).count()
    if existing > 0:
        return

    for rm_data in SEED_ROLE_MODELS:
        qualities_data = rm_data.pop("qualities")
        role_model = RoleModel(**rm_data)
        db.add(role_model)
        db.flush()

        for q_data in qualities_data:
            db.add(RoleModelQuality(
                role_model_id=role_model.id,
                quality_name=q_data["quality_name"],
                description=q_data["description"],
                suggested_activities=json.dumps(q_data["suggested_activities"], ensure_ascii=False),
            ))

    db.commit()


def list_role_models(db: Session) -> list[dict]:
    seed_role_models(db)
    models = db.query(RoleModel).filter(RoleModel.is_active == True).order_by(RoleModel.id).all()
    result = []
    for rm in models:
        rm_dict = {
            "id": rm.id,
            "name": rm.name,
            "field": rm.field,
            "avatar": rm.avatar,
            "image_url": rm.image_url or "",
            "description": rm.description,
            "qualities": [],
        }
        for q in rm.qualities:
            activities = json.loads(q.suggested_activities) if q.suggested_activities else []
            rm_dict["qualities"].append({
                "id": q.id,
                "role_model_id": q.role_model_id,
                "quality_name": q.quality_name,
                "description": q.description,
                "suggested_activities": activities,
            })
        result.append(rm_dict)
    return result


def get_role_model_detail(db: Session, role_model_id: int) -> dict | None:
    seed_role_models(db)
    rm = db.query(RoleModel).filter(RoleModel.id == role_model_id, RoleModel.is_active == True).first()
    if not rm:
        return None

    rm_dict = {
        "id": rm.id,
        "name": rm.name,
        "field": rm.field,
        "avatar": rm.avatar,
        "image_url": rm.image_url or "",
        "description": rm.description,
        "qualities": [],
    }
    for q in rm.qualities:
        activities = json.loads(q.suggested_activities) if q.suggested_activities else []
        rm_dict["qualities"].append({
            "id": q.id,
            "role_model_id": q.role_model_id,
            "quality_name": q.quality_name,
            "description": q.description,
            "suggested_activities": activities,
        })
    return rm_dict


def update_image_url(db: Session, role_model_id: int, image_url: str) -> bool:
    rm = db.query(RoleModel).filter(RoleModel.id == role_model_id).first()
    if not rm:
        return False
    rm.image_url = image_url
    db.commit()
    return True


def adopt_quality(db: Session, role_model_id: int, quality_id: int) -> dict | None:
    """采纳明星的品质为目标：创建 Quality + levels + category_mappings"""
    seed_role_models(db)

    rm_quality = db.query(RoleModelQuality).filter(
        RoleModelQuality.id == quality_id,
        RoleModelQuality.role_model_id == role_model_id,
    ).first()
    if not rm_quality:
        return None

    role_model = db.query(RoleModel).filter(RoleModel.id == role_model_id).first()

    # 检查同名 quality 是否已存在
    existing = db.query(Quality).filter(
        Quality.name == rm_quality.quality_name,
        Quality.is_active == True,
    ).first()
    if existing:
        return {
            "quality_id": existing.id,
            "quality_name": existing.name,
            "role_model_name": role_model.name,
            "message": f"品质'{existing.name}'已存在，无需重复创建。在Dashboard查看进度。",
        }

    # 创建 Quality
    quality = Quality(
        name=rm_quality.quality_name,
        description=f"以{role_model.name}为榜样：{rm_quality.description[:150]}",
        icon=role_model.avatar,
        target_level=5,
    )
    db.add(quality)
    db.flush()

    # 创建默认5级阶梯
    for level, name, desc, threshold in DEFAULT_LEVELS:
        db.add(QualityLevel(
            quality_id=quality.id,
            level=level,
            name=name,
            description=desc,
            threshold_score=threshold,
        ))

    # 根据推荐活动创建 CategoryMapping
    activities = json.loads(rm_quality.suggested_activities) if rm_quality.suggested_activities else []
    categories_seen = set()
    for act in activities:
        cat = act["category"]
        if cat not in categories_seen:
            categories_seen.add(cat)
            db.add(CategoryMapping(
                quality_id=quality.id,
                category=cat,
                score_per_duration=0.05 if cat in ("学习", "工作", "生活", "阅读") else 0.1,
                score_per_completion=5,
            ))

    db.commit()
    db.refresh(quality)

    return {
        "quality_id": quality.id,
        "quality_name": quality.name,
        "role_model_name": role_model.name,
        "message": f"已创建品质'{quality.name}'，系统将根据日常打卡自动计算积分。去Dashboard开始成长吧！",
    }
