<script setup lang="ts">
import { computed } from 'vue'
import { creatureSources, gaps, materialFacts, materialUses, recipeForItem, sources } from './catalog'
import type { Recipe } from './catalog'

const props = defineProps<{ name: string }>()
const emit = defineEmits<{ inspect: [recipe: Recipe] }>()
const fact = computed(() => materialFacts[props.name])
const source = computed(() => fact.value && sources[fact.value.source])
const origins = computed(() => creatureSources.get(props.name) ?? [])
const madeBy = computed(() => recipeForItem.get(props.name))
const uses = computed(() => {
  const recipes = materialUses.get(props.name) ?? []
  return (['craft', 'cook'] as const).flatMap(kind => {
    const names = [...new Set(recipes.filter(recipe => recipe.kind === kind).map(recipe => recipe.name))]
    if (!names.length) return []
    const examples = names.slice(0, 3).join('、')
    return [(kind === 'craft' ? '制作' : '料理投料：') + examples + (names.length > 3 ? '等 ' + names.length + ' 种' : '')]
  })
})
</script>

<template>
  <section class="material-info" :aria-label="name + '的用途与来源'">
    <h2>{{ name }}</h2>
    <dl>
      <dt>用途</dt>
      <dd>{{ [fact?.use, ...uses].filter(Boolean).join('；') || '尚未收录用途。' }}</dd>
      <dt>获取方式</dt>
      <dd>
        <span v-if="fact?.origin">{{ fact.origin }}</span>
        <span v-if="!madeBy && gaps[name]">（配方用量待核对）</span>
        <button v-if="madeBy" class="text-action" type="button" @click="emit('inspect', madeBy)">
          {{ madeBy.kind === 'cook' ? '查看料理记录' : '查看制作记录' }}
        </button>
        <span v-if="!fact?.origin && !madeBy && !origins.length">尚未核实。</span>
        <details v-if="origins.length" :key="name" :open="origins.length <= 6">
          <summary>相关生物 · {{ origins.length }} 种</summary>
          <div class="origin-list">
            <a v-for="origin in origins" :key="origin.sourceUrl" :href="origin.sourceUrl"
              target="_blank" rel="noopener noreferrer">{{ origin.name }} ↗</a>
          </div>
          <small>4399 社区记录，获取概率与数量待核对。</small>
        </details>
      </dd>
    </dl>
    <a v-if="source" class="material-citation" :href="source.revisionUrl ?? source.url"
      target="_blank" rel="noopener noreferrer">{{ source.title }} · {{ source.updated }} 历史资料 ↗</a>
  </section>
</template>
