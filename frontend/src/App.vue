<script setup lang="ts">
import AgentSidebar from '@/components/agent/AgentPanel.vue'
</script>

<template>
  <div class="app-layout">
    <main class="main-area">
      <router-view />
    </main>
    <aside class="agent-sidebar">
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
.agent-sidebar {
  width: 380px;
  flex-shrink: 0;
  border-left: 1px solid var(--color-border);
  background: var(--color-card);
}
</style>
