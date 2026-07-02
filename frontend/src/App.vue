<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import AgentSidebar from '@/components/agent/AgentPanel.vue'

const sidebarWidth = ref(380)
const isDragging = ref(false)

let startX = 0
let startWidth = 0

function onMouseDown(e: MouseEvent) {
  isDragging.value = true
  startX = e.clientX
  startWidth = sidebarWidth.value
  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'col-resize'
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

function onMouseMove(e: MouseEvent) {
  if (!isDragging.value) return
  const delta = startX - e.clientX
  const newWidth = Math.min(800, Math.max(280, startWidth + delta))
  sidebarWidth.value = newWidth
}

function onMouseUp() {
  isDragging.value = false
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)
}

onUnmounted(() => {
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)
})
</script>

<template>
  <div class="app-layout" :class="{ 'is-dragging': isDragging }">
    <main class="main-area">
      <router-view />
    </main>
    <div class="split-handle" @mousedown="onMouseDown"></div>
    <aside class="agent-sidebar" :style="{ width: sidebarWidth + 'px' }">
      <AgentSidebar />
    </aside>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
.main-area {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}
.split-handle {
  width: 4px;
  cursor: col-resize;
  flex-shrink: 0;
  background: var(--color-border);
  transition: background 0.15s;
  position: relative;
}
.split-handle:hover,
.is-dragging .split-handle {
  background: #6366f1;
}
.split-handle::after {
  content: '';
  position: absolute;
  inset: 0 -4px;
}
.agent-sidebar {
  flex-shrink: 0;
  background: var(--color-card);
}
</style>
