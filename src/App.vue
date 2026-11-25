<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import RecipeTree from './RecipeTree.vue'
import MaterialInfo from './MaterialInfo.vue'
import {
  checkedAt, ingredientNames, materialUses, materials, officialUrl, officialVersion, recipeForItem,
  recipeKey, recipeSearchTerms, recipes, sources, technologies, wikiRules, wikiSources, wikiUrl,
} from './catalog'
import type { Recipe } from './catalog'
import { findMissing, planRecipe } from './planner'
import type { Inventory } from './planner'

type Tab = 'all' | 'craft' | 'material' | 'cook'

const tabs: { key: Tab; label: string; icon: string }[] = [
  { key: 'all', label: '全部', icon: '' },
  { key: 'craft', label: '合成配方', icon: 'hammer' },
  { key: 'material', label: '材料反查', icon: 'layers' },
  { key: 'cook', label: '料理查询', icon: 'pot' },
]
const storageKey = 'jikunhuangye-helper.state.v1'
const maxStock = 99_999
const maxBatches = 999
const orderedRecipes = [...recipes].sort((a, b) => Number(a.kind === 'cook') - Number(b.kind === 'cook'))
const quickMaterials = ['树枝', '木头', '草', '燧石'].filter(item => materials.includes(item))
const statFields = [
  { key: 'health', label: '生命', icon: '♥' },
  { key: 'hunger', label: '饥饿', icon: '◒' },
  { key: 'sanity', label: '理智', icon: '✦' },
] as const
const craftPurposes = [...new Set(recipes.filter(recipe => recipe.kind === 'craft').map(recipe => recipe.category))]
const purposeGroups = [
  {
    kind: 'craft',
    label: '合成用途',
    options: craftPurposes.map(category => ({
      value: 'craft:' + category,
      label: category === '科学' ? '科技' : category,
    })),
  },
  {
    kind: 'cook',
    label: '料理效果',
    options: statFields.map(field => ({ value: 'cook:' + field.key, label: '回复' + field.label })),
  },
]

function matchesPurpose(recipe: Recipe, value: string) {
  if (!value) return true
  if (recipe.kind === 'craft') return value === 'craft:' + recipe.category
  const field = statFields.find(stat => value === 'cook:' + stat.key)
  const recorded = field ? recipe.food?.[field.key] : undefined
  return !!recorded && recorded.split('+').reduce((total, part) => total + Number(part), 0) > 0
}

function wholeNumber(value: unknown, maximum: number) {
  const number = Number(value)
  return Number.isFinite(number) ? Math.min(maximum, Math.max(0, Math.trunc(number))) : 0
}

const storageError = ref(false)
function readState(): { bag: Inventory; tech: string[] } {
  try {
    const raw = localStorage.getItem(storageKey)
    const state = raw ? JSON.parse(raw) : {}
    return {
      bag: Object.fromEntries(Object.entries(state?.bag ?? {})
        .filter(([name, amount]) => materials.includes(name) && typeof amount === 'number')
        .map(([name, amount]): [string, number] => [name, wholeNumber(amount, maxStock)])
        .filter(([, amount]) => amount > 0)),
      tech: Array.isArray(state?.tech) ? technologies.filter(name => state.tech.includes(name)) : [],
    }
  } catch {
    storageError.value = true
    return { bag: {}, tech: [] }
  }
}

const saved = readState()
const bag = ref<Inventory>(saved.bag)
const tech = ref<string[]>(saved.tech)
watch([bag, tech], () => {
  try {
    localStorage.setItem(storageKey, JSON.stringify({ bag: bag.value, tech: tech.value }))
    storageError.value = false
  } catch {
    storageError.value = true
  }
}, { deep: true })

const activeTab = ref<Tab>('all')
const search = ref('')
const material = ref('')
const purpose = ref('')
const filter = ref<'all' | 'materials' | 'ready'>('all')
const selectedKey = ref('')
const previousKeys = ref<string[]>([])
const mobileDetail = ref(false)
const batches = ref(1)
const detailSection = ref<HTMLElement | null>(null)
const catalogSection = ref<HTMLElement | null>(null)
const recipeList = ref<HTMLUListElement | null>(null)
const searchInput = ref<HTMLInputElement | null>(null)
const bagSection = ref<HTMLElement | null>(null)
const sourceDialog = ref<HTMLDialogElement | null>(null)
const bagDialog = ref<HTMLDialogElement | null>(null)
const bagMedia = window.matchMedia('(max-width: 1024px)')
const compact = ref(bagMedia.matches)

function syncBagLayout(event: MediaQueryListEvent) {
  if (!event.matches) bagDialog.value?.close()
  compact.value = event.matches
}

onMounted(() => bagMedia.addEventListener('change', syncBagLayout))
onUnmounted(() => bagMedia.removeEventListener('change', syncBagLayout))

const normalize = (input: string) => input.normalize('NFKC').trim().toLowerCase()
const materialNames = new Set(materials)
const searchIndex = orderedRecipes.map(recipe => ({
  recipe,
  name: normalize(recipe.name),
  ingredients: ingredientNames(recipe).map(normalize),
}))
const searchWord = computed(() => normalize(search.value))
const searchedMaterial = computed(() => material.value || searchWord.value)
const showMaterial = computed(() => activeTab.value !== 'cook' && materialNames.has(searchedMaterial.value))
const searchingForIronPick = computed(() => !material.value
  && (activeTab.value === 'all' || activeTab.value === 'craft')
  && /^铁镐子?$/.test(searchWord.value))
const waitingForMaterial = computed(() => activeTab.value === 'material' && !searchWord.value)
const cookingOnly = computed(() => activeTab.value === 'cook' || purpose.value.startsWith('cook:'))
const availablePurposeGroups = computed(() => {
  const tab = activeTab.value
  return tab === 'craft' || tab === 'cook' ? purposeGroups.filter(group => group.kind === tab) : purposeGroups
})
const chosenPurpose = computed(() =>
  availablePurposeGroups.value.flatMap(group => group.options).find(option => option.value === purpose.value),
)
const matchingMaterials = computed(() => {
  if (material.value) return []
  if (!searchWord.value) return quickMaterials
  return materials.filter(item => normalize(item).includes(searchWord.value))
    .sort((a, b) => Number(normalize(b) === searchWord.value) - Number(normalize(a) === searchWord.value))
    .slice(0, 6)
})

function status(recipe: Recipe, times = 1) {
  if (!recipe.ingredients) {
    return { label: recipe.kind === 'craft' ? '待实机核对' : '参考条目', tone: 'neutral' }
  }
  const count = findMissing(recipe, bag.value, times).length
  if (count) return { label: '缺 ' + count + ' 种材料', tone: 'amber' }
  if (recipe.kind === 'cook') return { label: '食材齐', tone: 'green' }
  if (!recipe.technology) return { label: '材料齐 · 科技待查', tone: 'neutral' }
  if (recipe.technology.some(item => !tech.value.includes(item))) {
    return { label: '材料齐 · 缺科技', tone: 'amber' }
  }
  return { label: '材料与科技齐', tone: 'green' }
}

function searchRank({recipe, name, ingredients}: typeof searchIndex[number]) {
  const query = searchWord.value
  if (!query) return 1
  if (activeTab.value !== 'material') {
    if (name === query) return 4
    if (name.includes(query)) return 3
    if (recipeSearchTerms[recipe.name]?.includes(query)) return 3
  }
  if (ingredients.includes(query)) return 2
  return Number(ingredients.some(name => name.includes(query)))
}

const matchingRecipes = computed(() => {
  if (waitingForMaterial.value) return []
  const matches = material.value ? (materialUses.get(material.value) ?? []).map(recipe => ({ recipe, rank: 1 }))
    : searchIndex.map(entry => ({ recipe: entry.recipe, rank: searchRank(entry) })).filter(entry => entry.rank)
  return matches.sort((a, b) => b.rank - a.rank || Number(Boolean(b.recipe.ingredients)) - Number(Boolean(a.recipe.ingredients))
    || Number(a.recipe.kind === 'cook') - Number(b.recipe.kind === 'cook')).map(entry => entry.recipe)
})
const visibleRecipes = computed(() => matchingRecipes.value.filter(recipe => {
  const tab = activeTab.value
  if ((tab === 'craft' || tab === 'cook') && recipe.kind !== tab) return false
  if (!matchesPurpose(recipe, purpose.value)) return false
  if (filter.value === 'all') return true
  if (!recipe.ingredients || findMissing(recipe, bag.value).length) return false
  return filter.value === 'materials' || (
    recipe.kind === 'craft' && recipe.technology &&
    recipe.technology.every(item => tech.value.includes(item))
  )
}))

const pageSize = 32
const renderLimit = ref(pageSize)
const renderedRecipes = computed(() => visibleRecipes.value.slice(0, renderLimit.value)
  .map(recipe => ({ recipe, state: status(recipe) })))
function extendList(event: Event) {
  const list = event.currentTarget as HTMLElement
  if (renderLimit.value < visibleRecipes.value.length && list.scrollHeight - list.scrollTop - list.clientHeight < 130) {
    renderLimit.value += pageSize
  }
}

const selected = computed(() =>
  recipes.find(recipe => recipeKey(recipe) === selectedKey.value) ?? visibleRecipes.value[0],
)
watch(() => selected.value && recipeKey(selected.value), () => { batches.value = 1 })
const source = computed(() => selected.value ? sources[selected.value.source] : undefined)
const selectedSourceUrl = computed(() => selected.value?.sourceUrl ?? source.value?.revisionUrl ?? source.value?.url)
const directMissing = computed(() => selected.value ? findMissing(selected.value, bag.value, batches.value) : [])
const plan = computed(() => selected.value ? planRecipe(selected.value, batches.value, bag.value) : null)
const planTechMissing = computed(() => plan.value?.requiredTechnology.filter(item => !tech.value.includes(item)) ?? [])

function resetSelection() {
  renderLimit.value = pageSize
  selectedKey.value = ''
  previousKeys.value = []
  mobileDetail.value = false
  void nextTick(() => recipeList.value?.scrollTo({ top: 0 }))
}

function clearFilters() {
  purpose.value = ''
  filter.value = 'all'
  resetSelection()
}

function applyPurpose() {
  if (cookingOnly.value && filter.value === 'ready') filter.value = 'materials'
  resetSelection()
}

function switchTab(tab: Tab) {
  if (activeTab.value === tab) return
  activeTab.value = tab
  if (!chosenPurpose.value) purpose.value = ''
  applyPurpose()
}

function selectRecipe(recipe: Recipe) {
  selectedKey.value = recipeKey(recipe)
  previousKeys.value = []
  mobileDetail.value = true
  if (window.matchMedia('(max-width: 700px)').matches) {
    void nextTick(() => detailSection.value?.focus())
  }
}

function inspectRecipe(item: string) {
  const recipe = recipeForItem.get(item)
  if (!recipe || !selected.value || recipe === selected.value) return
  previousKeys.value.push(recipeKey(selected.value))
  selectedKey.value = recipeKey(recipe)
  void nextTick(() => detailSection.value?.focus())
}

function previousRecipe() {
  const key = previousKeys.value.pop()
  if (!key) return
  selectedKey.value = key
  void nextTick(() => detailSection.value?.focus())
}

function showResults() {
  mobileDetail.value = false
  if (previousKeys.value.length) {
    selectedKey.value = previousKeys.value[0]
    previousKeys.value = []
  }
  void nextTick(() => {
    const target = catalogSection.value?.querySelector<HTMLElement>('[aria-pressed="true"]') ?? catalogSection.value
    target?.focus()
  })
}

function chooseMaterial(item: string) {
  const wasDetail = mobileDetail.value
  activeTab.value = 'material'
  material.value = item
  search.value = item
  resetSelection()
  if (wasDetail && window.matchMedia('(max-width: 700px)').matches) {
    void nextTick(() => catalogSection.value?.focus())
  }
}

function updateSearch() {
  material.value = ''
  resetSelection()
}

function clearSearch() {
  search.value = ''
  updateSearch()
  void nextTick(() => searchInput.value?.focus())
}

function submitSearch() {
  if (showMaterial.value && (activeTab.value === 'material' || !recipeForItem.has(searchedMaterial.value))) {
    chooseMaterial(searchedMaterial.value)
    return
  }
  const first = visibleRecipes.value[0]
  if (!first) return
  selectRecipe(first)
  void nextTick(() => detailSection.value?.focus())
}

function updateBatches(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.value && input.validity.valid) batches.value = input.valueAsNumber
  if (event.type === 'blur') input.value = String(batches.value)
}

const bagQuery = ref('')
const bagItem = ref('')
const bagDraft = ref<number | string>(1)
const quantityInput = ref<HTMLInputElement | null>(null)
const bagEntries = computed(() => Object.entries(bag.value).sort(([a], [b]) => a.localeCompare(b, 'zh-CN')))
const bagMatches = computed(() => {
  const query = normalize(bagQuery.value)
  return (query
    ? materials.filter(item => normalize(item).includes(query)).slice(0, 8)
    : quickMaterials)
})

function editBag(item: string) {
  bagItem.value = item
  bagDraft.value = bag.value[item] ?? 1
  void nextTick(() => {
    quantityInput.value?.focus()
    quantityInput.value?.select()
  })
}

function setQuantity(item: string, value: unknown) {
  const amount = wholeNumber(value, maxStock)
  if (amount) bag.value[item] = amount
  else delete bag.value[item]
  if (bagItem.value === item) bagDraft.value = amount
}

function updateIngredientQuantity(item: string, event: Event) {
  const input = event.target as HTMLInputElement
  const finishing = event.type === 'blur'
  if (input.validity.valid && (input.value || finishing)) {
    if (selected.value) selectedKey.value = recipeKey(selected.value)
    setQuantity(item, input.value)
  }
  if (finishing) input.value = String(bag.value[item] ?? 0)
}

function saveQuantity() {
  if (!bagItem.value) return
  setQuantity(bagItem.value, bagDraft.value)
  bagItem.value = ''
  bagQuery.value = ''
}

function showSources() {
  sourceDialog.value?.showModal()
}

function showBag() {
  if (compact.value) bagDialog.value?.showModal()
  else bagSection.value?.focus()
}
</script>

<template>
  <header class="masthead">
    <div class="shell">
      <div class="header-inner">
        <div class="brand">
          <span class="brand-icon icon" aria-hidden="true"></span>
          <div>
            <h1>荒野合成手册</h1>
            <p>《饥困荒野》手游</p>
          </div>
        </div>
        <div class="header-actions">
          <button type="button" class="header-source" @click="showSources">数据来源</button>
          <button type="button" class="header-bag" :aria-haspopup="compact ? 'dialog' : undefined" @click="showBag">
            <span class="icon backpack" aria-hidden="true"></span>背包
            <span v-if="bagEntries.length" class="bag-count">{{ bagEntries.length }}</span>
          </button>
        </div>
      </div>
    </div>
  </header>

  <main class="shell">
    <section class="workspace" :class="{ 'show-detail': mobileDetail }" aria-label="配方查询">
      <div class="workspace-search">
        <form class="query-form" role="search" @submit.prevent="submitSearch">
          <label class="search-field query-field">
            <span class="icon search-icon" aria-hidden="true"></span>
            <input ref="searchInput" v-model="search" type="search" aria-label="搜索成品或材料"
              :placeholder="activeTab === 'material' ? '搜索材料，例如树枝' : '搜索成品或材料，例如木甲、树枝'"
              @input="updateSearch">
          </label>
          <button v-if="search" type="button" class="search-clear" aria-label="清除搜索" @click="clearSearch">
            <span class="icon close-icon" aria-hidden="true"></span>
          </button>
          <button type="submit" class="search-submit">查找</button>
        </form>
        <div class="lookup-filters">
          <label class="select-field lookup-filter" :class="{ 'filter-active': purpose }">
            <span class="sr-only">用途筛选</span>
            <select v-model="purpose" @change="applyPurpose">
              <option value="">全部用途</option>
              <optgroup v-for="group in availablePurposeGroups" :key="group.kind" :label="group.label">
                <option v-for="option in group.options" :key="option.value" :value="option.value">{{ option.label }}</option>
              </optgroup>
            </select>
          </label>
          <label class="select-field lookup-filter" :class="{ 'filter-active': filter !== 'all' }">
            <span class="sr-only">背包筛选</span>
            <select v-model="filter" @change="resetSelection">
              <option value="all">全部状态</option>
              <option value="materials">{{ cookingOnly ? '食材齐全' : '材料齐全' }}</option>
              <option v-if="!cookingOnly" value="ready">材料与科技齐全</option>
            </select>
          </label>
        </div>
      </div>
      <div class="lookup-controls">
        <div class="lookup-toolbar">
          <nav class="tabs" aria-label="查询方式">
            <button v-for="tab in tabs" :key="tab.key" type="button" :aria-pressed="activeTab === tab.key"
              @click="switchTab(tab.key)">
              <span v-if="tab.icon" class="icon" :class="tab.icon" aria-hidden="true"></span>{{ tab.label }}
            </button>
          </nav>
          <div v-if="material || matchingMaterials.length" class="material-matches">
            <span class="material-label">{{ material || searchWord ? '按材料反查' : '常用材料' }}</span>
            <button v-if="material" class="chip selected-material" type="button" :aria-label="'清除材料筛选 ' + material"
              @click="clearSearch">{{ material }} <span aria-hidden="true">×</span></button>
            <button v-for="item in matchingMaterials" :key="item" type="button" class="chip"
              @click="chooseMaterial(item)">{{ item }}</button>
          </div>
        </div>
        <p v-if="searchingForIronPick" class="lookup-hint">「铁镐」名称待实机确认，已按相关采矿工具搜索。</p>
        <MaterialInfo v-if="showMaterial" :name="searchedMaterial" @inspect="selectRecipe" />
      </div>
      <div class="lookup">
        <div v-if="waitingForMaterial" class="reverse-empty">
          <span class="item-symbol" aria-hidden="true"><span class="icon layers"></span></span>
          <div>
            <h2>用这种材料能做什么？</h2>
            <p>输入材料名，或选择上方的常用材料。</p>
          </div>
        </div>
        <div v-else class="lookup-columns" :class="{ 'single-column': !selected }">
          <section ref="catalogSection" class="catalog" aria-label="查询结果" tabindex="-1">
            <div class="panel-heading">
              <h2>{{ material ? '使用' + material + '的配方' : searchWord ? '搜索结果' : chosenPurpose?.label ?? (activeTab === 'cook' ? '料理目录' : '配方目录') }}</h2>
              <span class="count" aria-live="polite">{{ visibleRecipes.length }} 条</span>
            </div>
            <ul v-if="visibleRecipes.length" ref="recipeList" class="recipe-list" @scroll.passive="extendList">
              <li v-for="{ recipe, state } in renderedRecipes" :key="recipeKey(recipe)">
                <button class="recipe-entry" type="button" :aria-pressed="selected === recipe" @click="selectRecipe(recipe)">
                  <span class="item-symbol" :class="recipe.kind" aria-hidden="true">
                    <span class="icon" :class="recipe.kind === 'cook' ? 'pot' : 'hammer'"></span>
                  </span>
                  <span class="recipe-entry-text">
                    <strong>{{ recipe.name }}{{ recipe.variant ? ' · ' + recipe.variant : '' }}</strong>
                    <span class="recipe-meta">
                      <span v-if="recipe.kind === 'craft'" class="recipe-category">{{ recipe.category }}</span>
                      <span class="recipe-materials">{{ ingredientNames(recipe).slice(0, 3).join(' · ') || (recipe.kind === 'cook' ? recipe.category : '') }}</span>
                    </span>
                  </span>
                  <span class="state" :class="state.tone">{{ state.label }}</span>
                </button>
              </li>
              <li v-if="visibleRecipes.length > renderLimit">
                <button type="button" class="small-button load-recipes" @click="renderLimit += pageSize">显示更多配方</button>
              </li>
            </ul>
            <div v-else class="empty">
              <p>{{ purpose || filter !== 'all' ? '没有符合当前筛选的配方。' : '没找到匹配的配方。' }}</p>
              <div class="empty-actions">
                <button v-if="purpose || filter !== 'all'" type="button" class="text-action" @click="clearFilters">清除筛选</button>
                <button v-if="search" type="button" class="text-action" @click="clearSearch">清除搜索</button>
              </div>
            </div>
          </section>

          <section v-if="selected" ref="detailSection" class="recipe-detail" aria-label="配方详情" tabindex="-1">
            <div class="detail-navigation">
              <button type="button" class="text-action back-results" @click="showResults">‹ 返回结果</button>
              <button v-if="previousKeys.length" type="button" class="text-action" @click="previousRecipe">‹ 上一配方</button>
            </div>
            <template v-if="selected && source">
              <div class="detail-head">
                <div>
                  <h2>{{ selected.name }}{{ selected.variant ? ' · ' + selected.variant : '' }}</h2>
                  <span class="detail-category">{{ selected.category }} · {{ source.evidence === 'game' ? '正式服实机核对' : source.evidence === 'official' ? '官方攻略' : source.evidence === 'guide' ? '社区资料' : '历史图鉴' }}</span>
                </div>
                <span class="state" :class="status(selected, batches).tone">{{ status(selected, batches).label }}</span>
              </div>

              <div v-if="selected.kind === 'craft' && (selected.ingredients || selected.technology)" class="tech-line">
                <span>科技</span>
                <strong v-if="!selected.technology">未记录</strong>
                <strong v-else-if="!selected.technology.length">无需科技</strong>
                <strong v-else>{{ selected.technology.join('、') }}</strong>
                <span v-if="selected.unlocks" class="muted">解锁 {{ selected.unlocks }}</span>
              </div>

              <div v-if="selected.food" class="food-stats" aria-label="料理属性">
                <div v-for="field in statFields" :key="field.key">
                  <span><span class="stat-icon" aria-hidden="true">{{ field.icon }}</span> {{ field.label }}</span>
                  <strong>{{ selected.food[field.key] ?? '—' }}</strong>
                </div>
              </div>
              <dl v-if="selected.food" class="food-facts">
                <div v-if="selected.food.criteria"><dt>烹饪需求</dt><dd>{{ selected.food.criteria }}</dd></div>
                <div v-if="selected.food.restriction"><dt>图鉴限制</dt><dd>{{ selected.food.restriction }}</dd></div>
                <div v-if="selected.food.seconds"><dt>用时</dt><dd>{{ selected.food.seconds }} 秒</dd></div>
                <div v-if="selected.food.shelfLife"><dt>腐烂天数</dt><dd>{{ selected.food.shelfLife }} 天</dd></div>
              </dl>

              <template v-if="selected.ingredients && plan">
                <div class="ingredient-heading">
                  <h3 v-if="source.evidence === 'game'">实机用量</h3>
                  <h3 v-else-if="source.evidence === 'official'">{{ selected.kind === 'cook' ? '官方投料示例' : '官方攻略用量' }}</h3>
                  <h3 v-else-if="source.evidence === 'guide'">公开资料参考用量</h3>
                  <h3 v-else>{{ selected.kind === 'cook' ? 'Wiki 投料示例' : '历史参考用量' }}</h3>
                  <label class="batches">
                    制作次数
                    <input type="number" min="1" :max="maxBatches" step="1" inputmode="numeric" :value="batches"
                      @input="updateBatches" @blur="updateBatches" @keydown.enter.prevent="($event.target as HTMLInputElement).blur()">
                  </label>
                </div>
                <ul class="ingredients">
                  <li class="ingredient-labels" aria-hidden="true"><span>材料</span><span>背包 / 需求</span></li>
                  <li v-for="entry in selected.ingredients" :key="entry.item">
                    <button type="button" class="text-action" :aria-label="'反查' + entry.item"
                      @click="chooseMaterial(entry.item)">{{ entry.item }}</button>
                    <div class="ingredient-stock" :class="{ enough: (bag[entry.item] ?? 0) >= entry.quantity * batches }">
                      <input class="stock-input" type="number" min="0" :max="maxStock" step="1" inputmode="numeric"
                        :value="bag[entry.item] ?? 0" :aria-label="entry.item + '背包数量'"
                        @focus="($event.target as HTMLInputElement).select()"
                        @input="updateIngredientQuantity(entry.item, $event)"
                        @blur="updateIngredientQuantity(entry.item, $event)"
                        @keydown.enter.prevent="($event.target as HTMLInputElement).blur()">
                      <span>/</span><span class="needed-quantity" :aria-label="'需要 ' + entry.quantity * batches">{{ entry.quantity * batches }}</span>
                    </div>
                  </li>
                </ul>
                <div class="missing-box" :class="{ met: !directMissing.length }" aria-live="polite">
                  <strong>{{ directMissing.length ? '当前还缺' : selected.kind === 'cook' ? '示例食材齐全' : '直接材料齐全' }}</strong>
                  <span v-if="directMissing.length">{{ directMissing.map(entry => entry.item + ' ×' + entry.quantity).join('、') }}</span>
                </div>
                <details class="tree-box" :key="recipeKey(selected)" :open="plan.tree.some(node => node.children.length > 0)">
                  <summary>合成树</summary>
                  <p v-if="plan.missing.length" class="tree-summary">
                    展开后仍缺 {{ plan.missing.map(entry => entry.item + ' ×' + entry.quantity).join('、') }}
                  </p>
                  <p v-else class="tree-summary">展开后材料齐全</p>
                  <p v-if="planTechMissing.length" class="tree-summary">还需科技 {{ planTechMissing.join('、') }}</p>
                  <p v-if="plan.unknownTechnology" class="tree-summary">合成链有科技条件待核实。</p>
                  <RecipeTree :nodes="plan.tree" @inspect="inspectRecipe" />
                </details>
              </template>
              <div v-else class="reference-box">
                <h3>{{ selected.kind === 'cook' ? 'Wiki 料理记录' : '正式服配方待核对' }}</h3>
                <p>{{ selected.reference || (selected.kind === 'craft' ? '以游戏内制作栏显示的材料和数量为准。' : '目前缺少可计算的配方。') }}</p>
              </div>

              <p v-if="selected.note" class="detail-note">{{ selected.note }}</p>
              <p v-if="selected.food && source.evidence !== 'official'" class="detail-note">投料例和食材度数来自旧图鉴，锅中结果以游戏为准。</p>
              <p class="detail-source">
                <a v-if="selectedSourceUrl" :href="selectedSourceUrl" target="_blank" rel="noopener noreferrer">{{ source.title }} ↗</a>
                <span v-else>{{ source.title }}</span>
                <span v-if="source.gameVersion">{{ source.gameVersion }}</span>
                <span v-if="source.updated">{{ source.updated }}</span>
              </p>
            </template>
            <p v-else class="empty">找到配方后，可在这里查看材料和来源。</p>
          </section>
        </div>
      </div>

      <Teleport defer to="#backpack-sheet" :disabled="!compact">
      <aside id="backpack" ref="bagSection" class="backpack-panel" aria-labelledby="bag-title" tabindex="-1">
        <div class="panel-heading">
          <h2 id="bag-title"><span class="icon backpack" aria-hidden="true"></span> 我的背包</h2>
          <div class="bag-actions">
            <span class="count">{{ bagEntries.length }} 种</span>
            <form v-if="compact" method="dialog">
              <button class="small-button" type="submit">关闭</button>
            </form>
          </div>
        </div>
        <div class="bag-content">
          <label class="search-field">
            <span class="icon search-icon" aria-hidden="true"></span>
            <input v-model="bagQuery" type="search" aria-label="搜索背包材料" placeholder="搜索要录入的材料">
          </label>
          <div class="bag-matches">
            <button v-for="item in bagMatches" :key="item" type="button" class="chip"
              :aria-pressed="bagItem === item" @click="editBag(item)">{{ item }}</button>
            <p v-if="!bagMatches.length" class="muted">没有匹配的已收录材料。</p>
          </div>
          <form v-if="bagItem" class="bag-form" @submit.prevent="saveQuantity">
            <label>
              <span>{{ bagItem }}数量</span>
              <input ref="quantityInput" v-model="bagDraft" type="number" min="0" :max="maxStock"
                step="1" inputmode="numeric" required>
            </label>
            <button class="primary-button" type="submit">保存</button>
            <button class="small-button" type="button" @click="bagItem = ''">取消</button>
            <button type="button" class="text-action" @click="bagDialog?.close(); chooseMaterial(bagItem); searchInput?.focus()">查用途与来源</button>
          </form>

          <ul v-if="bagEntries.length" class="bag-list">
            <li v-for="[item, quantity] in bagEntries" :key="item">
              <button type="button" class="text-action bag-item" :aria-label="'修改' + item + '数量'"
                @click="editBag(item)">{{ item }}</button>
              <div class="stepper">
                <button type="button" :aria-label="item + '减一'" @click="setQuantity(item, quantity - 1)">−</button>
                <output :aria-label="item + '已录入数量'">{{ quantity }}</output>
                <button type="button" :aria-label="item + '加一'" :disabled="quantity >= maxStock" @click="setQuantity(item, quantity + 1)">+</button>
              </div>
            </li>
          </ul>
          <div v-else class="bag-empty">
            <span class="icon backpack" aria-hidden="true"></span>
            <p>还没有记录材料</p>
          </div>

          <div v-if="technologies.length" class="technology">
            <h3>已解锁科技</h3>
            <label v-for="item in technologies" :key="item" class="tech-option">
              <input v-model="tech" type="checkbox" :value="item"> {{ item }}
            </label>
          </div>
          <p v-if="storageError" class="storage-note error" role="status">浏览器存储不可用，刷新后可能丢失本次录入。</p>
          <p v-else class="storage-note">背包保存在当前浏览器。筛选按单次用量。</p>
        </div>
      </aside>
      </Teleport>
    </section>

    <footer class="footer">
      <span>正式服 {{ officialVersion }} 配方以游戏内制作栏为准</span>
      <button type="button" class="text-action" @click="showSources">来源与数据缺口</button>
    </footer>
  </main>

  <dialog id="backpack-sheet" ref="bagDialog" class="backpack-sheet" aria-labelledby="bag-title"></dialog>

  <dialog ref="sourceDialog" class="source-dialog" aria-labelledby="source-title">
    <div class="dialog-heading">
      <h2 id="source-title">来源与数据缺口</h2>
      <form method="dialog"><button class="small-button" type="submit">关闭</button></form>
    </div>
    <p>核对日期 {{ checkedAt }}。配方来自游戏内截图、公开攻略和历史图鉴，详情标明了用量的出处。</p>
    <ul class="source-list">
      <li v-for="page in wikiSources" :key="page.title">
        <a :href="page.revisionUrl ?? page.url" target="_blank" rel="noopener noreferrer">{{ page.title }}</a>
        <span>{{ page.updated }} · rev {{ page.revision }}</span>
      </li>
      <li>
        <a :href="sources['guide-magic'].url" target="_blank" rel="noopener noreferrer">家园速生指南 · 图 02、29、32</a>
        <span>2024-03-18 · rev 1718</span>
      </li>
      <li>
        <a href="https://jihuang.qq.com/cp/a20230420xjy/pc/page-news-detail.html?docid=9125582025783670033" target="_blank" rel="noopener noreferrer">腾讯《饥荒科技手册》</a>
        <span>基础合成与科技</span>
      </li>
      <li v-for="key in ['official-tool-guide', 'official-food-guide', 'official-farming', 'handbook-tools']" :key="key">
        <a :href="sources[key].url" target="_blank" rel="noopener noreferrer">{{ sources[key].title }}</a>
        <span>公开配方参考</span>
      </li>
    </ul>
    <p>正式上线版本为 {{ officialVersion }}。背包与合成树按已收录用量计算，正式服配方以游戏内显示为准。<a :href="officialUrl" target="_blank" rel="noopener noreferrer">官方公告</a></p>
    <p>公开资料缺少完整配方或用量有出入的条目，仍标为「待实机核对」。部分科技条件、单次产量和料理规则也有缺项。</p>
    <p>4399 和 Wiki 的批量转载许可未确认。本站仅整理物品名称、数值和来源关系，各条可查原页。
      <a href="https://www.4399.com/notice/banquan.htm" target="_blank" rel="noopener noreferrer">4399 声明</a> ·
      <a :href="wikiRules" target="_blank" rel="noopener noreferrer">BWIKI 社区规则</a> · <a :href="wikiUrl" target="_blank" rel="noopener noreferrer">Wiki 首页</a></p>
  </dialog>
</template>
