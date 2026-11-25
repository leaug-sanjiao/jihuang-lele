<script setup lang="ts">
import { gaps, sources } from './catalog'
import type { PlanNode } from './planner'

defineProps<{ nodes: PlanNode[] }>()
defineEmits<{ inspect: [item: string] }>()
</script>

<template>
  <ul class="recipe-tree">
    <li v-for="node in nodes" :key="node.item">
      <div class="tree-row">
        <button v-if="node.recipe" type="button" class="text-action" @click="$emit('inspect', node.item)">
          {{ node.item }}
        </button>
        <a v-else-if="gaps[node.item]" :href="sources[gaps[node.item].source].url"
          target="_blank" rel="noopener noreferrer">{{ node.item }}</a>
        <strong v-else>{{ node.item }}</strong>
        <span class="tree-quantity">× {{ node.quantity }}</span>
        <span v-if="node.fromBag" class="muted">已分配 {{ node.fromBag }}</span>
        <span v-if="node.batches" class="state green">先制作 {{ node.batches }} 次</span>
        <span v-if="node.missing" class="state amber">还缺 {{ node.missing }}</span>
      </div>
      <p v-if="node.reason && (node.recipe || gaps[node.item])" class="tree-note">{{ node.reason }}</p>
      <p v-if="node.missing && node.recipe?.reference" class="tree-note">{{ node.recipe.reference }}</p>
      <RecipeTree v-if="node.children.length" :nodes="node.children" @inspect="$emit('inspect', $event)" />
    </li>
  </ul>
</template>
