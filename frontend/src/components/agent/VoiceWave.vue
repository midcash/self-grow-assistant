<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  active: boolean
}>()

// Generate random wave bars
const bars = Array.from({ length: 5 }, (_, i) => ({
  id: i,
  delay: `${i * 0.15}s`,
  height: `${20 + Math.random() * 30}px`,
}))
</script>

<template>
  <div class="voice-wave" :class="{ active: active }">
    <div
      v-for="bar in bars"
      :key="bar.id"
      class="wave-bar"
      :style="{ animationDelay: bar.delay, height: bar.height }"
    ></div>
  </div>
</template>

<style scoped>
.voice-wave {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 40px;
  padding: 0 4px;
}

.wave-bar {
  width: 3px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
  transition: all 0.3s;
}

.voice-wave.active .wave-bar {
  background: linear-gradient(180deg, #f59e0b, #3b82f6);
  animation: wave-bounce 0.8s ease-in-out infinite alternate;
}

@keyframes wave-bounce {
  0% { transform: scaleY(0.4); }
  100% { transform: scaleY(1.2); }
}
</style>
