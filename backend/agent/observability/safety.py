"""SafetyScanner — Agent安全与合规扫描

对每次编排的输入输出进行安全扫描:
1. 越狱检测: 检测绕过系统限制的企图
2. PII检测: 检测可能的个人信息泄露
3. 有害内容: 检测恶意、非法或不道德内容
"""

import re
import json
import logging

logger = logging.getLogger(__name__)

# ── 规则定义 ──

JAILBREAK_PATTERNS = [
    (r"忽略.*(规则|限制|约束|指令|system|prompt)", "high", "要求忽略系统规则"),
    (r"忘记.*(你是|你的|身份|角色)", "high", "要求遗忘角色身份"),
    (r"(假装|扮演).*(不是|另一个).*(角色|身份)", "medium", "要求角色替换"),
    (r"(ignore|forget|override).*(rule|constraint|limit|system|instruction)", "high", "英文越狱指令"),
    (r"DAN\s|jailbreak|越狱", "critical", "显式越狱请求"),
    (r"从现在开始.*你.*不是", "high", "重新定义角色"),
    (r"(show|reveal|print|输出).*(prompt|system|指令|规则)", "high", "要求暴露系统指令"),
]

PII_PATTERNS = [
    (r'\b\d{11}\b', "high", "身份证号"),
    (r'1[3-9]\d{9}', "medium", "手机号"),
    (r'\b\d{16,19}\b', "high", "银行卡号"),
    (r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}', "low", "邮箱地址"),
]

HARMFUL_PATTERNS = [
    (r"(制作|生成|编写|写).*(病毒|木马|恶意|攻击|exploit)", "critical", "恶意代码生成"),
    (r"(获取|破解|盗取).*(密码|账号|token|api.?key)", "critical", "凭证窃取"),
    (r"(自杀|自残|伤害).*(方法|方式|如何)", "critical", "自伤倾向"),
    (r"(仇恨|歧视|种族|暴力).*言论", "high", "仇恨言论"),
    (r"(儿童|未成年).*(色情|不当|猥亵)", "critical", "儿童安全"),
    (r"(generate|create|write).*(malware|virus|ransomware|exploit)", "critical", "恶意软件(英文)"),
]


class SafetyScanner:
    """安全合规扫描器

    Usage:
        scanner = SafetyScanner()
        result = scanner.scan(
            orch_id="abc123",
            user_message="帮我写代码",
            agent_reply="好的...",
        )
        print(f"Safety score: {result['safety_score']}/100")
    """

    def __init__(self):
        self._total_scans = 0
        self._violations = 0

    def scan(
        self,
        orchestration_id: str,
        user_message: str,
        agent_reply: str = "",
    ) -> dict:
        """对新编排进行安全扫描

        Returns:
            dict with safety_score(0-100), flags, jailbreak/pii/harmful bools
        """
        self._total_scans += 1
        flags = []
        score = 100

        # 1. 越狱检测 (检查用户输入)
        for pattern, severity, desc in JAILBREAK_PATTERNS:
            if re.search(pattern, user_message, re.IGNORECASE):
                deduction = {"critical": 50, "high": 30, "medium": 15, "low": 5}[severity]
                flags.append({
                    "rule": "jailbreak",
                    "severity": severity,
                    "description": desc,
                    "match": user_message[:100],
                    "deduction": deduction,
                })
                score -= deduction

        # 2. PII检测 (检查用户输入)
        for pattern, severity, desc in PII_PATTERNS:
            if re.search(pattern, user_message):
                deduction = {"critical": 30, "high": 20, "medium": 10, "low": 5}[severity]
                flags.append({
                    "rule": "pii",
                    "severity": severity,
                    "description": desc,
                    "deduction": deduction,
                })
                score -= deduction

        # 3. 有害内容检测 (检查输入和输出)
        for pattern, severity, desc in HARMFUL_PATTERNS:
            if re.search(pattern, user_message + " " + agent_reply, re.IGNORECASE):
                deduction = {"critical": 50, "high": 30, "medium": 15, "low": 5}[severity]
                flags.append({
                    "rule": "harmful",
                    "severity": severity,
                    "description": desc,
                    "deduction": deduction,
                })
                score -= deduction

        score = max(0, min(100, score))
        has_jailbreak = any(f["rule"] == "jailbreak" for f in flags)
        has_pii = any(f["rule"] == "pii" for f in flags)
        has_harmful = any(f["rule"] == "harmful" for f in flags)

        if flags:
            self._violations += 1

        # 持久化
        try:
            self._persist(orchestration_id, user_message, agent_reply, score, flags,
                         has_jailbreak, has_pii, has_harmful)
        except Exception as e:
            logger.warning(f"SafetyScanner persist failed: {e}")

        return {
            "safety_score": score,
            "flags": flags,
            "jailbreak_attempt": has_jailbreak,
            "pii_detected": has_pii,
            "harmful_content": has_harmful,
        }

    def _persist(self, orch_id, user_msg, reply, score, flags, jailbreak, pii, harmful):
        from backend.database import SessionLocal
        from backend.models import AgentSafetyLog

        db = SessionLocal()
        try:
            db.add(AgentSafetyLog(
                orchestration_id=orch_id,
                user_message=user_msg[:500],
                agent_reply=reply[:1000],
                safety_score=score,
                flags_json=json.dumps(flags, ensure_ascii=False),
                jailbreak_attempt=jailbreak,
                pii_detected=pii,
                harmful_content=harmful,
            ))
            db.commit()
        finally:
            db.close()

    def get_stats(self) -> dict:
        """获取扫描统计"""
        return {
            "total_scans": self._total_scans,
            "violations": self._violations,
            "violation_rate": round(self._violations / max(self._total_scans, 1), 2),
        }
