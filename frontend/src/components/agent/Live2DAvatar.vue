<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useAgent } from '@/composables/useAgent'
import { getAgentStatus } from '@/api/agent'
import AgentPanel from './AgentPanel.vue'
import EmotionBadge from './EmotionBadge.vue'

declare global {
  interface Window {
    L2Dwidget: any
  }
}

const {
  isOpen, isSpeaking, hasAlerts, unreadAlerts, emotionTag, messages,
  togglePanel, init: initAgent, currentAudio,
} = useAgent()

const isHovered = ref(false)
const isModelReady = ref(false)
const live2dEnabled = ref(false)

const EMOTION_MAP: Record<string, string> = {
  HAPPY: ':)', WORRIED: ':(', URGENT: '!!', CALM: '~', THINKING: '?', ENCOURAGE: '!',
}

onMounted(async () => {
  initAgent()
  try {
    const status = await getAgentStatus()
    live2dEnabled.value = status.config?.live2d_enabled || false
  } catch {
    live2dEnabled.value = false
  }
  if (live2dEnabled.value) {
    await loadLive2DScript()
    initLive2DWidget()
  }
})

function loadLive2DScript(): Promise<void> {
  return new Promise((resolve) => {
    if (window.L2Dwidget) { resolve(); return }
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/live2d-widget@3.0.4/lib/L2Dwidget.min.js'
    script.onload = () => resolve()
    script.onerror = () => { console.warn('L2Dwidget CDN failed'); resolve() }
    document.body.appendChild(script)
  })
}

function initLive2DWidget() {
  if (typeof window.L2Dwidget === 'undefined') return
  try {
    window.L2Dwidget.init({
      model: {
        jsonPath: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-shizuku@1.0.5/assets/shizuku.model.json',
        scale: 1,
      },
      display: { position: 'right', width: 140, height: 260, hOffset: 0, vOffset: -60 },
      mobile: { show: true, scale: 0.5 },
      react: { opacityDefault: 0.7, opacityOnHover: 0.2 },
      dialog: {
        enable: true, hitokoto: false,
        script: { 'tap body': '有什么可以帮你的吗？', 'tap face': '嘻嘻...' },
      },
    })
    const tryAttach = setInterval(() => {
      const widget = document.querySelector('#live2d-widget')
      const canvas = widget?.querySelector('canvas')
      if (canvas && !(canvas as any).__panelHooked) {
        ;(canvas as any).__panelHooked = true
        canvas.style.pointerEvents = 'auto'
        canvas.addEventListener('click', (e: MouseEvent) => {
          e.stopPropagation(); e.preventDefault(); togglePanel()
        })
        isModelReady.value = true
        clearInterval(tryAttach)
      }
    }, 500)
    setTimeout(() => clearInterval(tryAttach), 10000)
  } catch (e) {
    console.warn('L2Dwidget init failed:', e)
  }
}

// ── Audio-driven lip sync via timeupdate (~4Hz) ──
let _timeupdateHandler: (() => void) | null = null

watch(isSpeaking, (speaking) => {
  if (!isModelReady.value || !live2dEnabled.value) return
  if (speaking) {
    const agentMsgs = messages.value.filter((m: any) => m.role === 'agent')
    const last = agentMsgs[agentMsgs.length - 1]
    if (!last || !window.L2Dwidget) return
    // Show dialog bubble
    const short = last.content.slice(0, 60) + (last.content.length > 60 ? '...' : '')
    try { window.L2Dwidget.alert(short) } catch {}

    // Hook audio timeupdate for mouth movement
    const audio = currentAudio.value
    if (!audio) return
    let lastPos = 0
    _timeupdateHandler = () => {
      if (!audio || audio.paused) return
      if (Math.abs(audio.currentTime - lastPos) < 0.2) return
      lastPos = audio.currentTime
      const canvas = document.querySelector('#live2d-widget canvas') as HTMLElement | null
      if (canvas) {
        canvas.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
        setTimeout(() => canvas.dispatchEvent(new MouseEvent('mouseup', { bubbles: true })), 100)
      }
    }
    audio.addEventListener('timeupdate', _timeupdateHandler)
  } else {
    if (_timeupdateHandler && currentAudio.value) {
      currentAudio.value.removeEventListener('timeupdate', _timeupdateHandler)
      _timeupdateHandler = null
    }
  }
})

watch(emotionTag, (tag) => {
  if (!isModelReady.value || !window.L2Dwidget) return
  const msg = EMOTION_MAP[tag]
  if (msg) { try { window.L2Dwidget.alert(msg) } catch {} }
})
</script>

<template>
  <div class="live2d-container">
    <Transition name="panel-slide">
      <AgentPanel v-if="isOpen" />
    </Transition>
    <button
      v-if="!live2dEnabled"
      class="simple-avatar"
      :class="{ 'has-alerts': hasAlerts }"
      @click="togglePanel"
      title="打开助手"
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="8" r="4"/>
        <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
      </svg>
      <span v-if="hasAlerts" class="simple-badge">{{ unreadAlerts > 99 ? '99+' : unreadAlerts }}</span>
    </button>
    <div
      v-if="!live2dEnabled && isHovered && !isOpen"
      class="avatar-tooltip"
      @mouseenter="isHovered = true"
      @mouseleave="isHovered = false"
    >
      {{ hasAlerts ? `${unreadAlerts} 个任务需关注` : '唤出助手' }}
    </div>
  </div>
</template>

<style scoped>
.live2d-container {
  position: fixed;
  bottom: 100px;
  right: 16px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}
.simple-avatar {
  width: 52px; height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1a1a2e, #16213e);
  border: 2px solid rgba(245, 158, 11, 0.25);
  color: rgba(245, 158, 11, 0.6);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.3s;
  position: relative;
}
.simple-avatar:hover {
  border-color: rgba(245, 158, 11, 0.6); color: rgba(245, 158, 11, 0.9); transform: scale(1.08);
}
.simple-avatar.has-alerts { border-color: rgba(239, 68, 68, 0.4); }
.simple-badge {
  position: absolute; top: -4px; right: -4px;
  min-width: 18px; height: 18px; border-radius: 9px;
  background: #ef4444; color: #fff;
  font-size: 10px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  padding: 0 4px;
}
.avatar-tooltip {
  position: absolute; bottom: 100%; right: 0; margin-bottom: 8px;
  background: rgba(0, 0, 0, 0.85); color: #f59e0b;
  padding: 6px 12px; border-radius: 8px;
  font-size: 12px; white-space: nowrap; pointer-events: none;
}
.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0; transform: translateY(20px) scale(0.95);
}
</style>
