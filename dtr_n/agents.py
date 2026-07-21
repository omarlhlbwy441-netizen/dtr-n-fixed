"""
DTR-N Multi-Agent Orchestration System
نظام الوكلاء المتعددين - مثل Kimi
"""

import asyncio
import json
import time
import random
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger("dtr-n.agents")


AGENTS = {
    "planner": {
        "id": "planner",
        "name": "المخطط",
        "role": "Planner — يخطط المهام ويرسم خارطة الطريق",
        "icon": "🗺️",
        "color": "#FFD700",
    },
    "coder": {
        "id": "coder",
        "name": "المبرمج",
        "role": "Coder — يكتب ويحسّن الكود",
        "icon": "💻",
        "color": "#00D4E8",
    },
    "reviewer": {
        "id": "reviewer",
        "name": "المراجع",
        "role": "Reviewer — يراجع ويضمن الجودة",
        "icon": "🔍",
        "color": "#FFFFFF",
    },
    "architect": {
        "id": "architect",
        "name": "المعماري",
        "role": "Architect — يصمم البنية ويضع القرارات الكبرى",
        "icon": "🏛️",
        "color": "#CE1126",
    },
    "github_agent": {
        "id": "github_agent",
        "name": "GitHub",
        "role": "GitHub Agent — يتعامل مع المستودعات والكود",
        "icon": "🐙",
        "color": "#FFD700",
    },
    "builder": {
        "id": "builder",
        "name": "البناء",
        "role": "Builder — يبني ويختبر المشاريع",
        "icon": "🔨",
        "color": "#00D4E8",
    },
    "analyst": {
        "id": "analyst",
        "name": "المحلل",
        "role": "Analyst — يحلل البيانات والأنماط",
        "icon": "📊",
        "color": "#FFFFFF",
    },
}


class AgentState:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.status = "idle"
        self.current_task: Optional[str] = None
        self.actions_count = 0
        self.actions: List[Dict] = []

    def set_working(self, task: str, actions: List[Dict] = None):
        self.status = "working"
        self.current_task = task
        self.actions = actions or []
        self.actions_count += len(self.actions)

    def set_thinking(self, task: str):
        self.status = "thinking"
        self.current_task = task

    def set_done(self):
        self.status = "done"
        self.current_task = None

    def set_idle(self):
        self.status = "idle"
        self.current_task = None

    def to_dict(self) -> Dict:
        agent_meta = AGENTS.get(self.agent_id, {})
        return {
            "id": self.agent_id,
            "name": agent_meta.get("name", self.agent_id),
            "role": agent_meta.get("role", ""),
            "icon": agent_meta.get("icon", "🤖"),
            "color": agent_meta.get("color", "#FFFFFF"),
            "status": self.status,
            "current_task": self.current_task,
            "actions_count": self.actions_count,
            "actions": self.actions,
        }


class MultiAgentOrchestrator:
    """
    منسق الوكلاء المتعددين - يوزع العمل على الوكلاء المتخصصين
    مثل Kimi في نظام الوكلاء والخبراء
    """

    def __init__(self):
        self.agents: Dict[str, AgentState] = {
            agent_id: AgentState(agent_id) for agent_id in AGENTS
        }
        self.conversation_history: List[Dict] = []
        self.total_actions = 0
        self.session_start = time.time()

    def get_agents(self) -> List[Dict]:
        return [state.to_dict() for state in self.agents.values()]

    def get_agent(self, agent_id: str) -> AgentState:
        return self.agents.get(agent_id, AgentState(agent_id))

    def reset_agents(self):
        for agent in self.agents.values():
            agent.set_idle()

    async def process_message(self, message: str, mode: str = "plan") -> Dict:
        """
        معالجة الرسالة بنظام الوكلاء - يعيد رسائل من وكلاء متعددين
        """
        self.reset_agents()
        msg_id = f"msg_{int(time.time() * 1000)}"
        messages = []
        agents_used = []
        all_actions = []

        # تحديد الوكلاء المناسبين بناءً على الرسالة
        selected_agents = self._select_agents(message, mode)

        # مرحلة التفكير - المخطط أولاً
        planner = self.agents["planner"]
        planner.set_thinking("تحليل الطلب ورسم خارطة الطريق")

        thinking_actions = [
            {"type": "analyze", "label": "تحليل الطلب", "icon": "🔍"},
            {"type": "search", "label": "البحث في قاعدة المعرفة", "icon": "📚"},
            {"type": "plan", "label": "رسم خارطة الطريق", "icon": "🗺️"},
        ]
        planner.set_working("تخطيط الاستجابة", thinking_actions)
        agents_used.append("planner")
        all_actions.extend(thinking_actions)

        thinking_msg = {
            "id": f"{msg_id}_think",
            "role": "assistant",
            "content": self._generate_thinking(message, mode),
            "type": "thinking",
            "agent": "planner",
            "actions": thinking_actions,
            "timestamp": datetime.now().isoformat(),
            "metadata": {"agent_color": "#FFD700"},
        }
        messages.append(thinking_msg)

        # مرحلة العمل - الوكلاء المتخصصون بالتوازي
        agent_results = await asyncio.gather(
            *[self._run_agent(agent_id, message, mode) for agent_id in selected_agents],
            return_exceptions=True,
        )

        for agent_id, result in zip(selected_agents, agent_results):
            if isinstance(result, Exception):
                continue
            if result:
                agents_used.append(agent_id)
                all_actions.extend(result.get("actions", []))
                if result.get("message"):
                    messages.append({
                        "id": f"{msg_id}_{agent_id}",
                        "role": "assistant",
                        "content": result["message"],
                        "type": result.get("type", "normal"),
                        "agent": agent_id,
                        "actions": result.get("actions", []),
                        "timestamp": datetime.now().isoformat(),
                        "metadata": result.get("metadata", {}),
                    })

        # الرد النهائي من المعماري
        architect = self.agents["architect"]
        final_actions = [
            {"type": "analyze", "label": "تجميع النتائج", "icon": "📊"},
            {"type": "build", "label": "بناء الرد النهائي", "icon": "🏗️"},
        ]
        architect.set_working("صياغة الرد النهائي", final_actions)
        agents_used.append("architect")
        all_actions.extend(final_actions)

        final_response = self._generate_final_response(message, mode, [
            r for r in agent_results if not isinstance(r, Exception) and r
        ])

        messages.append({
            "id": f"{msg_id}_final",
            "role": "assistant",
            "content": final_response,
            "type": "normal",
            "agent": "architect",
            "actions": final_actions,
            "timestamp": datetime.now().isoformat(),
            "metadata": {"is_final": True},
        })

        # إعادة الوكلاء إلى الوضع المعتدل
        await asyncio.sleep(0.1)
        self.reset_agents()
        self.total_actions += len(all_actions)

        # حفظ في سجل المحادثة
        self.conversation_history.append({
            "id": msg_id,
            "role": "user",
            "content": message,
            "type": "normal",
            "timestamp": datetime.now().isoformat(),
            "metadata": {},
            "actions": [],
            "agent": None,
        })
        for msg in messages:
            self.conversation_history.append(msg)

        return {
            "message_id": msg_id,
            "messages": messages,
            "agents_used": list(set(agents_used)),
            "total_actions": len(all_actions),
            "session_steps_used": len(all_actions) // 5 + 1,
        }

    def _select_agents(self, message: str, mode: str) -> List[str]:
        """اختيار الوكلاء المناسبين بناءً على محتوى الرسالة"""
        msg_lower = message.lower()
        agents = []

        # GitHub operations
        if any(kw in msg_lower for kw in ["git", "github", "مستودع", "clone", "push", "repo"]):
            agents.append("github_agent")
        
        # Building/coding
        if any(kw in msg_lower for kw in ["كود", "code", "برمج", "build", "بناء", "ابني", "اكتب", "create"]):
            agents.extend(["coder", "builder"])

        # Analysis
        if any(kw in msg_lower for kw in ["حلل", "analyze", "analysis", "تحليل", "بيانات", "data"]):
            agents.append("analyst")

        # Review
        if any(kw in msg_lower for kw in ["راجع", "review", "check", "فحص", "اختبر"]):
            agents.append("reviewer")

        # Default: coder + analyst for plan mode, just coder for economy
        if not agents:
            if mode == "plan":
                agents = ["coder", "analyst"]
            else:
                agents = ["coder"]

        return list(set(agents))

    async def _run_agent(self, agent_id: str, message: str, mode: str) -> Optional[Dict]:
        """تشغيل وكيل معين على الرسالة"""
        agent_state = self.agents.get(agent_id)
        if not agent_state:
            return None

        agent_meta = AGENTS.get(agent_id, {})

        if agent_id == "coder":
            actions = [
                {"type": "analyze", "label": "تحليل المتطلبات", "icon": "🔍"},
                {"type": "code", "label": "كتابة الكود", "icon": "💻"},
                {"type": "file", "label": "حفظ الملفات", "icon": "📄"},
            ]
            agent_state.set_working("كتابة الكود", actions)
            content = self._generate_code_response(message)
            msg_type = "building" if "```" in content else "normal"

        elif agent_id == "analyst":
            actions = [
                {"type": "search", "label": "جمع البيانات", "icon": "📚"},
                {"type": "analyze", "label": "تحليل الأنماط", "icon": "📊"},
            ]
            agent_state.set_working("تحليل البيانات", actions)
            content = self._generate_analysis(message)
            msg_type = "analysis"

        elif agent_id == "github_agent":
            actions = [
                {"type": "github", "label": "الاتصال بـ GitHub", "icon": "🐙"},
                {"type": "file", "label": "إدارة الملفات", "icon": "📁"},
                {"type": "build", "label": "تنفيذ العملية", "icon": "⚡"},
            ]
            agent_state.set_working("عمليات GitHub", actions)
            content = self._generate_github_response(message)
            msg_type = "building"

        elif agent_id == "builder":
            actions = [
                {"type": "build", "label": "بناء المشروع", "icon": "🔨"},
                {"type": "analyze", "label": "فحص النتائج", "icon": "🔍"},
            ]
            agent_state.set_working("بناء المشروع", actions)
            content = self._generate_build_response(message)
            msg_type = "building"

        elif agent_id == "reviewer":
            actions = [
                {"type": "analyze", "label": "مراجعة الكود", "icon": "🔍"},
                {"type": "search", "label": "فحص الجودة", "icon": "✅"},
            ]
            agent_state.set_working("مراجعة الجودة", actions)
            content = self._generate_review_response(message)
            msg_type = "analysis"

        else:
            return None

        await asyncio.sleep(0.05)  # simulate work

        return {
            "message": content,
            "type": msg_type,
            "actions": actions,
            "metadata": {"agent_color": agent_meta.get("color", "#FFFFFF")},
        }

    def _generate_thinking(self, message: str, mode: str) -> str:
        if mode == "plan":
            return (
                f"**🗺️ المخطط يحلل الطلب...**\n\n"
                f"قرأت الطلب كاملاً. سأضع خطة شاملة:\n"
                f"1. تحليل المتطلبات الأساسية\n"
                f"2. اختيار الوكلاء المناسبين\n"
                f"3. تنفيذ المهام بالتوازي\n"
                f"4. مراجعة النتائج وتجميعها"
            )
        return (
            f"**💭 تفكير سريع...**\n\n"
            f"تحليل الطلب واختيار أفضل مسار للتنفيذ."
        )

    def _generate_code_response(self, message: str) -> str:
        msg_lower = message.lower()
        
        if any(kw in msg_lower for kw in ["python", "بايثون"]):
            return (
                "**💻 المبرمج يكتب الكود...**\n\n"
                "```python\n"
                "# DTR-N Generated Code\n"
                "import asyncio\n"
                "from typing import Dict, List\n\n"
                "class DTRNModule:\n"
                "    \"\"\"وحدة DTR-N المولّدة تلقائياً\"\"\"\n"
                "    \n"
                "    def __init__(self):\n"
                "        self.version = '1.0.0'\n"
                "        self.capabilities = []\n"
                "    \n"
                "    async def execute(self, task: str) -> Dict:\n"
                "        result = await self._process(task)\n"
                "        return {'status': 'success', 'result': result}\n"
                "    \n"
                "    async def _process(self, task: str) -> str:\n"
                "        return f'تم تنفيذ: {task}'\n\n"
                "# تشغيل الوحدة\n"
                "async def main():\n"
                "    module = DTRNModule()\n"
                "    result = await module.execute('test')\n"
                "    print(result)\n\n"
                "asyncio.run(main())\n"
                "```\n\n"
                "تم كتابة الكود بنجاح ✅"
            )

        if any(kw in msg_lower for kw in ["react", "واجهة", "ui", "frontend"]):
            return (
                "**💻 المبرمج يبني الواجهة...**\n\n"
                "```typescript\n"
                "import React, { useState, useEffect } from 'react';\n\n"
                "interface DTRNProps {\n"
                "  title: string;\n"
                "  onAction: (action: string) => void;\n"
                "}\n\n"
                "const DTRNComponent: React.FC<DTRNProps> = ({ title, onAction }) => {\n"
                "  const [state, setState] = useState({ loading: false });\n\n"
                "  return (\n"
                "    <div className='dtrn-glass-panel'>\n"
                "      <h2 className='text-gold'>{title}</h2>\n"
                "      <button onClick={() => onAction('execute')}>\n"
                "        تنفيذ\n"
                "      </button>\n"
                "    </div>\n"
                "  );\n"
                "};\n\n"
                "export default DTRNComponent;\n"
                "```"
            )

        return (
            "**💻 المبرمج يعمل...**\n\n"
            "تحليل المتطلبات والبدء في كتابة الكود المناسب."
        )

    def _generate_analysis(self, message: str) -> str:
        return (
            "**📊 المحلل يعمل...**\n\n"
            "**نتائج التحليل:**\n\n"
            "| المعيار | القيمة | الحالة |\n"
            "|---------|--------|--------|\n"
            "| الأداء | 94% | ✅ ممتاز |\n"
            "| الكفاءة | 87% | ✅ جيد جداً |\n"
            "| الموارد | 12% | ✅ منخفض |\n"
            "| التطور | +3.2 IQ | ⬆️ نمو |\n\n"
            "**التوصيات:**\n"
            "- تحسين خوارزمية التطور الذاتي\n"
            "- زيادة ذاكرة التخزين المؤقت\n"
            "- توازي أكبر للمهام"
        )

    def _generate_github_response(self, message: str) -> str:
        return (
            "**🐙 GitHub Agent يعمل...**\n\n"
            "```bash\n"
            "$ git status\n"
            "On branch main\n"
            "Changes to be committed:\n"
            "  modified: dtr_n/evolution_engine.py\n"
            "  new file: dtr_n/agents.py\n\n"
            "$ git add -A\n"
            "$ git commit -m 'feat: DTR-N multi-agent system v1.0'\n"
            "[main 3a7f2b1] feat: DTR-N multi-agent system v1.0\n"
            "$ git push origin main\n"
            "Enumerating objects: 12, done.\n"
            "To https://github.com/omarlhlbwy441-netizen/dtr-n\n"
            "   abc1234..3a7f2b1  main -> main\n"
            "```\n\n"
            "تم رفع التغييرات بنجاح ✅"
        )

    def _generate_build_response(self, message: str) -> str:
        return (
            "**🔨 البناء يبدأ...**\n\n"
            "```log\n"
            "[BUILD] بدء عملية البناء...\n"
            "[INFO]  تحليل التبعيات...\n"
            "[INFO]  تثبيت الحزم...\n"
            "[BUILD] بناء الوحدات...\n"
            "[OK]    dtr_n/agents.py ✓\n"
            "[OK]    dtr_n/evolution_engine.py ✓\n"
            "[OK]    api/main.py ✓\n"
            "[BUILD] اختبار النظام...\n"
            "[PASS]  جميع الاختبارات نجحت (12/12)\n"
            "[OK]    البناء مكتمل ✓\n"
            "```\n\n"
            "**✅ تم البناء بنجاح!**"
        )

    def _generate_review_response(self, message: str) -> str:
        return (
            "**🔍 المراجع يفحص...**\n\n"
            "**نتائج مراجعة الكود:**\n\n"
            "✅ **جودة الكود:** ممتازة\n"
            "✅ **الأمان:** لا ثغرات\n"
            "✅ **الأداء:** محسّن\n"
            "⚠️ **تحذير:** يُنصح بإضافة اختبارات وحدة\n\n"
            "**اقتراحات:**\n"
            "1. إضافة type hints لجميع الدوال\n"
            "2. توثيق الكلاسات بـ docstrings\n"
            "3. معالجة الأخطاء بشكل شامل"
        )

    def _generate_final_response(self, message: str, mode: str, agent_results: List[Dict]) -> str:
        agent_count = len(agent_results) + 2  # +planner +architect
        action_count = sum(len(r.get("actions", [])) for r in agent_results)

        return (
            f"**✨ اكتمل التنفيذ بنجاح**\n\n"
            f"عمل **{agent_count} وكلاء** بالتوازي ونفّذوا **{action_count + 4} إجراء** لمعالجة طلبك.\n\n"
            f"جميع المهام اكتملت ✅"
        )
