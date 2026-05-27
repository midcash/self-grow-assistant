<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  count: number
  emotion: string
}>()

const showBadge = computed(() => props.count > 0)

const badgeColor = computed(() => {
  if (props.emotion === 'URGENT' || props.emotion === 'WORRIED') return 'bg-red-500'
  if (props.emotion === 'THINKING') return 'bg-purple-500'
  return 'bg-amber-500'
})
</script>

<template>
  <Transition name="badge-pop">
    <div
      v-if="showBadge"
      class="emotion-badge"
      :class="badgeColor"
    >
      {{ count > 99 ? '99+' : count }}
    </div>
  </Transition>
</template>

<style scoped>
.emotion-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 20px;
  height: 20px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 0 5px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  z-index: 1;
}

.badge-pop-enter-active {
  animation: badge-pop 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.badge-pop-leave-active {
  animation: badge-pop 0.2s cubic-bezier(0.4, 0, 0.2, 1) reverse;
}

@keyframes badge-pop {
  0% { transform: scale(0); }
  60% { transform: scale(1.2); }
  100% { transform: scale(1); }
}
</style>
