"""Thêm từ tiếng Trung mẫu để test."""
from database import init_db, add_word

init_db()

sample_words = [
    ("你好", "nǐ hǎo", "xin chào", "你好，我叫Mai Hương。", "Xin chào, tôi tên là Mai Hương."),
    ("谢谢", "xiè xie", "cảm ơn", "谢谢你的帮助！", "Cảm ơn bạn đã giúp đỡ!"),
    ("美丽", "měilì", "đẹp, xinh đẹp", "她很美丽。", "Cô ấy rất đẹp."),
    ("学习", "xuéxí", "học tập", "我每天都学习汉语。", "Tôi học tiếng Trung mỗi ngày."),
    ("喜欢", "xǐhuān", "thích, yêu thích", "我喜欢吃越南菜。", "Tôi thích ăn món Việt."),
    ("朋友", "péngyǒu", "bạn bè", "她是我最好的朋友。", "Cô ấy là bạn thân nhất của tôi."),
    ("快乐", "kuàilè", "vui vẻ, hạnh phúc", "祝你生日快乐！", "Chúc bạn sinh nhật vui vẻ!"),
    ("工作", "gōngzuò", "công việc, làm việc", "你的工作怎么样？", "Công việc của bạn thế nào?"),
    ("家庭", "jiātíng", "gia đình", "我很爱我的家庭。", "Tôi rất yêu gia đình mình."),
    ("旅行", "lǚxíng", "du lịch", "我想去中国旅行。", "Tôi muốn đi du lịch Trung Quốc."),
    ("吃饭", "chīfàn", "ăn cơm, ăn bữa ăn", "我们一起去吃饭吧！", "Chúng ta cùng đi ăn cơm nhé!"),
    ("努力", "nǔlì", "nỗ lực, cố gắng", "要努力学习才能进步。", "Phải nỗ lực học tập mới tiến bộ được."),
]

for hanzi, pinyin, meaning, ex_zh, ex_vn in sample_words:
    add_word(hanzi, pinyin, meaning, ex_zh, ex_vn)

print(f"Đã thêm {len(sample_words)} từ tiếng Trung mẫu!")
