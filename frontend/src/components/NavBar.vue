<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()

const tabs = [
  { path: '/', label: '看板', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
  { path: '/input', label: '录入', icon: 'M12 4v16m8-8H4' },
  { path: '/checkin', label: '打卡', icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' },
  { path: '/qualities', label: '品质', icon: 'M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z' },
  { path: '/report', label: '报告', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
]

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<template>
  <nav class="bottom-nav">
    <div class="nav-inner">
      <router-link
        v-for="tab in tabs" :key="tab.path" :to="tab.path"
        class="nav-item"
        :class="{ active: isActive(tab.path) }"
      >
        <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" :d="tab.icon" />
        </svg>
        <span class="nav-label">{{ tab.label }}</span>
        <span v-if="isActive(tab.path)" class="nav-dot"></span>
      </router-link>
    </div>
  </nav>
</template>

<style scoped>
.bottom-nav {
  position: fixed; bottom: 0; left: 0; right: 380px;
  display: flex; justify-content: center; z-index: 50;
  padding-bottom: env(safe-area-inset-bottom);
}
.nav-inner {
  display: flex; justify-content: space-around;
  width: 100%; max-width: 480px;
  padding: 8px 0;
  background: var(--color-card);
  border-top: 1px solid var(--color-border);
}
.nav-item {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 4px 12px; border-radius: 8px; transition: color 0.2s;
  text-decoration: none;
  color: var(--color-text-muted);
}
.nav-item:hover { color: var(--color-text-light); }
.nav-item.active { color: var(--color-accent); }
.nav-icon { width: 24px; height: 24px; }
.nav-label { font-size: 11px; }
.nav-dot { width: 4px; height: 4px; border-radius: 50%; background: var(--color-accent); }
</style>
