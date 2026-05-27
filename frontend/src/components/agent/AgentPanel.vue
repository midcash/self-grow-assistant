<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useAgent } from '@/composables/useAgent'
import VoiceWave from './VoiceWave.vue'
import PriorityList from './PriorityList.vue'
import ActivityLog from './ActivityLog.vue'
import KnowledgeBase from './KnowledgeBase.vue'

const {
  isSpeaking, messages, emotionTag, priorityTasks, scheduleRunning, status,
  sendMessage, speak, evaluate, toggleScheduleRun,
} = useAgent()

const inputText = ref('')
const activeTab = ref<'chat' | 'tasks' | 'log' | 'kb'>('chat')
const isEvaluating = ref(false)
const chatContainer = ref<HTMLDivElement>()

watch(() => messages.value.length, async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
})

const quickActions = [
  { label: '描绘未来的我', message: '如果我坚持现在的品质成长和目标推进，3个月后我会变成一个什么样的人？请描绘那个未来的我，告诉那个我哪里吸引人、值得现在的我为之努力。' },
  { label: '评估优先级', message: null, action: 'evaluate' as const },
  { label: '今日总结', message: '帮我总结一下今天的任务完成情况' },
]

async function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  inputText.value = ''
  const resp = await sendMessage(text)
  if (resp) speak(resp.reply)
}

async function handleQuickAction(action: typeof quickActions[0]) {
  if (action.action === 'evaluate') {
    isEvaluating.value = true
    await evaluate()
    isEvaluating.value = false
    activeTab.value = 'tasks'
    return
  }
  if (action.message) {
    const resp = await sendMessage(action.message)
    if (resp) speak(resp.reply)
  }
}
</script>

<template>
  <div class="sidebar-panel">
    <!-- Header -->
    <div class="panel-header">
      <div class="header-left">
        <div class="agent-avatar-mini">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
          </svg>
        </div>
        <div>
          <div class="agent-name">自我成长助手</div>
          <div class="agent-status">
            <span class="status-dot" :class="{ online: scheduleRunning }"></span>
            {{ scheduleRunning ? '监控中' : '待机' }}
            <span class="mcp-dot" :class="{ on: status?.config?.mcp_active }" title="MCP 知识库"></span>
            <span class="emotion-tag">[{{ emotionTag }}]</span>
          </div>
        </div>
      </div>
      <VoiceWave :active="isSpeaking" />
    </div>

    <!-- Tabs -->
    <div class="panel-tabs">
      <button class="tab-btn" :class="{ active: activeTab === 'chat' }" @click="activeTab = 'chat'">对话</button>
      <button class="tab-btn" :class="{ active: activeTab === 'tasks' }" @click="activeTab = 'tasks'">
        任务<span v-if="priorityTasks.length" class="tab-count">{{ priorityTasks.length }}</span>
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'log' }" @click="activeTab = 'log'">日志</button>
      <button class="tab-btn" :class="{ active: activeTab === 'kb' }" @click="activeTab = 'kb'">知识库</button>
    </div>

    <!-- Chat -->
    <div v-show="activeTab === 'chat'" class="chat-area">
      <div ref="chatContainer" class="chat-messages">
        <div v-if="messages.length === 0" class="welcome">
          <p>你好，我是你的成长助手。</p>
          <p>可以帮你分析任务优先级、拆解目标、提供心理辅导。</p>
        </div>
        <div v-for="(msg, idx) in messages" :key="idx" class="chat-bubble" :class="msg.role">
          <div class="bubble-content">{{ msg.content }}</div>
        </div>
      </div>
      <div class="quick-actions">
        <button v-for="a in quickActions" :key="a.label" class="quick-btn"
          :disabled="isEvaluating" @click="handleQuickAction(a)">
          {{ isEvaluating && a.action === 'evaluate' ? '评估中...' : a.label }}
        </button>
      </div>
      <div class="chat-input-area">
        <input v-model="inputText" class="chat-input" placeholder="输入消息..." @keyup.enter="handleSend" />
        <button class="send-btn" @click="handleSend" :disabled="!inputText.trim()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"/></svg>
        </button>
      </div>
    </div>

    <!-- Tasks -->
    <div v-show="activeTab === 'tasks'" class="tasks-area">
      <PriorityList />
    </div>

    <!-- Activity Log -->
    <div v-show="activeTab === 'log'" class="tab-area">
      <ActivityLog />
    </div>

    <!-- Knowledge Base -->
    <div v-show="activeTab === 'kb'" class="tab-area">
      <KnowledgeBase />
    </div>

    <!-- Footer -->
    <div class="panel-footer">
      <button class="footer-btn" :class="{ active: scheduleRunning }" @click="toggleScheduleRun">
        <span class="footer-dot" :class="{ on: scheduleRunning }"></span>
        {{ scheduleRunning ? '20分钟监控中' : '监控已暂停' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.sidebar-panel {
  display: flex; flex-direction: column;
  height: 100vh;
  background: var(--color-card);
}

/* Header */
.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}
.header-left { display: flex; align-items: center; gap: 10px; }
.agent-avatar-mini {
  width: 34px; height: 34px; border-radius: 50%;
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex; align-items: center; justify-content: center;
}
.agent-name { font-size: 14px; font-weight: 600; color: var(--color-text); }
.agent-status { font-size: 11px; color: var(--color-text-muted); display: flex; align-items: center; gap: 4px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-border); }
.status-dot.online { background: var(--color-success); }
.mcp-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-border); display: inline-block; }
.mcp-dot.on { background: var(--color-accent); }
.emotion-tag { color: var(--color-accent); }

/* Tabs */
.panel-tabs { display: flex; border-bottom: 1px solid var(--color-border); flex-shrink: 0; }
.tab-btn {
  flex: 1; padding: 10px; background: none; border: none;
  color: var(--color-text-muted); font-size: 13px; cursor: pointer;
  position: relative; display: flex; align-items: center; justify-content: center; gap: 4px;
}
.tab-btn.active { color: var(--color-accent); font-weight: 600; }
.tab-btn.active::after {
  content: ''; position: absolute; bottom: 0; left: 25%; width: 50%; height: 2px;
  background: var(--color-accent); border-radius: 1px;
}
.tab-count {
  font-size: 10px; background: var(--color-primary-light); color: var(--color-accent);
  padding: 0 5px; border-radius: 8px;
}

/* Chat */
.chat-area { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.chat-messages { flex: 1; overflow-y: auto; padding: 14px 16px; display: flex; flex-direction: column; gap: 8px; }
.welcome { text-align: center; padding: 28px 10px; }
.welcome p { font-size: 13px; color: var(--color-text-muted); margin: 4px 0; }
.chat-bubble { max-width: 88%; }
.chat-bubble.user { align-self: flex-end; }
.chat-bubble.user .bubble-content {
  background: var(--color-primary-light);
  color: var(--color-text);
  border-radius: 12px 12px 2px 12px;
}
.chat-bubble.agent .bubble-content {
  background: var(--color-bg);
  color: var(--color-text-light);
  border-radius: 12px 12px 12px 2px;
}
.bubble-content { padding: 9px 13px; font-size: 13px; line-height: 1.55; white-space: pre-wrap; }

/* Quick actions */
.quick-actions { display: flex; gap: 6px; padding: 0 16px 8px; flex-wrap: wrap; }
.quick-btn {
  font-size: 11px; padding: 4px 10px; border-radius: 12px;
  background: var(--color-bg); border: 1px solid var(--color-border);
  color: var(--color-text-muted); cursor: pointer; transition: all 0.2s;
}
.quick-btn:hover:not(:disabled) { border-color: var(--color-accent); color: var(--color-accent); }
.quick-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* Input */
.chat-input-area { display: flex; gap: 8px; padding: 10px 16px; border-top: 1px solid var(--color-border); }
.chat-input {
  flex: 1; background: var(--color-bg); border: 1px solid var(--color-border);
  border-radius: 8px; padding: 9px 13px; font-size: 13px; color: var(--color-text);
  outline: none; transition: border-color 0.2s;
}
.chat-input:focus { border-color: var(--color-accent); }
.chat-input::placeholder { color: var(--color-text-muted); }
.send-btn {
  width: 34px; height: 34px; border-radius: 8px;
  background: var(--color-primary-light); border: 1px solid var(--color-border);
  color: var(--color-accent); cursor: pointer;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.send-btn:hover:not(:disabled) { background: var(--color-accent); color: #fff; }
.send-btn:disabled { opacity: 0.3; cursor: not-allowed; }

/* Tasks */
.tasks-area { flex: 1; padding: 0 16px; overflow-y: auto; min-height: 0; }
.tab-area { flex: 1; overflow-y: auto; min-height: 0; display: flex; flex-direction: column; }

/* Footer */
.panel-footer { padding: 10px 16px; border-top: 1px solid var(--color-border); flex-shrink: 0; }
.footer-btn {
  width: 100%; padding: 7px; background: var(--color-bg); border: 1px solid var(--color-border);
  border-radius: 6px; color: var(--color-text-muted); font-size: 11px;
  cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;
}
.footer-btn:hover { background: var(--color-sidebar); color: var(--color-text-light); }
.footer-btn.active { border-color: var(--color-success); color: var(--color-success); }
.footer-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--color-border); }
.footer-dot.on { background: var(--color-success); }
</style>
