import { ref, computed } from 'vue'
import {
  getAgentStatus,
  agentChat,
  orchestrate,
  triggerEvaluation,
  getPriorityTasks,
  textToSpeech,
  getScheduleStatus,
  toggleSchedule,
  type AgentStatus,
  type PriorityTask,
  type EvaluateResult,
  type OrchestrateResult,
} from '@/api/agent'

// Singleton state shared across components
const isOpen = ref(false)
const isSpeaking = ref(false)
const isListening = ref(false)
const status = ref<AgentStatus>({ initialized: false })
const priorityTasks = ref<PriorityTask[]>([])
const scheduleRunning = ref(false)
const messages = ref<{ role: string; content: string }[]>([])
const emotionTag = ref('CALM')
const unreadAlerts = ref(0)

export function useAgent() {
  const hasAlerts = computed(() => unreadAlerts.value > 0)

  async function fetchStatus() {
    try {
      status.value = await getAgentStatus()
    } catch {
      status.value = { initialized: false }
    }
  }

  async function sendMessage(text: string) {
    messages.value.push({ role: 'user', content: text })
    try {
      // Auto-route: complex requests use multi-agent orchestration
      const shouldOrchestrate = _needsOrchestration(text)
      const history = messages.value.slice(0, -1)

      if (shouldOrchestrate) {
        const result = await orchestrate(text, history)
        messages.value.push({ role: 'agent', content: result.reply })
        emotionTag.value = 'THINKING'
        return { reply: result.reply, emotion_tag: 'THINKING' }
      } else {
        const resp = await agentChat(text, history)
        messages.value.push({ role: 'agent', content: resp.reply })
        emotionTag.value = resp.emotion_tag || 'CALM'
        return resp
      }
    } catch (e) {
      messages.value.push({ role: 'agent', content: '抱歉，我现在无法回复...' })
      return null
    }
  }

  function _needsOrchestration(text: string): boolean {
    // Complex task keywords → use multi-agent orchestration
    const complexKeywords = [
      '安排', '规划', '导游', '旅行', '攻略', '路线',
      '分析', '报告', '方案', '推荐', '建议',
      '计划', '日程', '帮我', '安排一下',
      '搜索', '查找', '查询', '检索', '知识库', '文档', '资料', 'MCP',
      '分解', '拆解', '规划目标', '目标分解', '拆分任务',
      '焦虑', '紧张', '压力', '自卑', '害怕', '担心', '难过', '沮丧',
    ]
    return text.length > 8 && complexKeywords.some(k => text.includes(k))
  }

  async function evaluate() {
    try {
      const result: EvaluateResult = await triggerEvaluation()
      priorityTasks.value = result.tasks
      unreadAlerts.value = result.alerts.length
      return result
    } catch {
      return null
    }
  }

  async function fetchPriorityTasks() {
    try {
      const data = await getPriorityTasks()
      priorityTasks.value = data.tasks
    } catch {
      priorityTasks.value = []
    }
  }

  // 当前播放的 Audio 对象（供 Live2D 绑定 timeupdate 事件）
  const currentAudio = ref<HTMLAudioElement | null>(null)

  function speak(text: string) {
    isSpeaking.value = true
    try {
      textToSpeech(text).then(blob => {
        const url = URL.createObjectURL(blob)
        const audio = new Audio(url)
        currentAudio.value = audio
        audio.onended = () => {
          isSpeaking.value = false
          currentAudio.value = null
          URL.revokeObjectURL(url)
        }
        audio.onerror = () => {
          isSpeaking.value = false
          currentAudio.value = null
          URL.revokeObjectURL(url)
        }
        audio.play()
      })
    } catch {
      isSpeaking.value = false
    }
  }

  async function fetchSchedule() {
    try {
      const s = await getScheduleStatus()
      scheduleRunning.value = s.running
    } catch {
      scheduleRunning.value = false
    }
  }

  async function toggleScheduleRun() {
    try {
      const r = await toggleSchedule()
      scheduleRunning.value = r.running
    } catch {
      // ignore
    }
  }

  function togglePanel() {
    isOpen.value = !isOpen.value
    if (isOpen.value) {
      unreadAlerts.value = 0
    }
  }

  async function init() {
    await Promise.all([
      fetchStatus(),
      fetchPriorityTasks(),
      fetchSchedule(),
    ])
  }

  return {
    // state
    isOpen,
    isSpeaking,
    isListening,
    status,
    priorityTasks,
    scheduleRunning,
    messages,
    emotionTag,
    unreadAlerts,
    hasAlerts,
    // audio ref (for Live2D timeupdate sync)
    currentAudio,
    // actions
    fetchStatus,
    sendMessage,
    evaluate,
    fetchPriorityTasks,
    speak,
    fetchSchedule,
    toggleScheduleRun,
    togglePanel,
    init,
  }
}
