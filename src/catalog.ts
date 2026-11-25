import snapshot from './data/wiki.json'
import supplement from './data/supplement.json'
import handbook from './data/handbook.json'

export interface Ingredient {
  item: string
  quantity: number
}

export interface Source {
  title: string
  url?: string
  evidence?: string
  updated?: string
  gameVersion?: string
  revision?: number
  revisionUrl?: string
  rowCount?: number
}

export interface Recipe {
  name: string
  variant?: string
  kind: 'craft' | 'cook'
  category: string
  ingredients: Ingredient[] | null
  source: string
  sourceUrl?: string
  technology?: string[]
  unlocks?: string
  output?: number
  reference?: string
  mentions?: string[]
  note?: string
  food?: {
    criteria?: string
    restriction?: string
    seconds?: string
    shelfLife?: string
    health?: string
    hunger?: string
    sanity?: string
  }
}

export const sources: Record<string, Source> = { ...snapshot.sources, ...supplement.sources }
export const recipeSearchTerms: Record<string, string[]> = supplement.searchTerms
export const wikiSources: Source[] = Object.values(snapshot.sources)
export const checkedAt = [snapshot.checkedAt, supplement.checkedAt, handbook.checkedAt].sort().at(-1)
export const officialVersion = '1.30.1'
export const officialUrl = 'https://www.taptap.cn/moment/872603097178833842'
export const wikiUrl = 'https://wiki.biligame.com/jikunhuangye/'
export const wikiRules = 'https://wiki.biligame.com/wiki/WIKI社区规则'
export const gaps: Record<string, { source: string }> = snapshot.gaps
export const recipeKey = (recipe: Recipe) => [recipe.kind, recipe.name, recipe.variant].filter(Boolean).join(':')
export const ingredientNames = (recipe: Recipe) =>
  recipe.ingredients?.map(({ item }) => item) ?? recipe.mentions ?? []

const catalog = new Map<string, Recipe>()
for (const entry of [...snapshot.recipes, ...supplement.recipes]) {
  if (entry.kind !== 'craft' && entry.kind !== 'cook') {
    throw new Error(`未知配方类别：${entry.name}`)
  }
  const recipe: Recipe = { ...entry, kind: entry.kind }
  catalog.set(recipeKey(recipe), recipe)
}

for (const entry of handbook.recipes) {
  const recipe: Recipe = { ...entry, kind: 'craft' }
  const key = recipeKey(recipe)
  if (!catalog.has(key)) catalog.set(key, recipe)
}
export const recipes = Array.from(catalog.values())
export const recipeForItem = new Map(recipes.filter(recipe => !recipe.variant).map(recipe => [recipe.name, recipe]))
export const materialFacts: Record<string, {source: string; origin?: string; use?: string}> = snapshot.materialFacts
export const materialUses = new Map<string, Recipe[]>()
for (const recipe of recipes) {
  for (const item of new Set(ingredientNames(recipe))) {
    const uses = materialUses.get(item) ?? []
    uses.push(recipe)
    materialUses.set(item, uses)
  }
}
export const creatureSources = new Map<string, { name: string; sourceUrl: string }[]>()
for (const creature of handbook.creatures) {
  for (const item of creature.drops) {
    const list = creatureSources.get(item) ?? []
    list.push(creature)
    creatureSources.set(item, list)
  }
}
export const materials = Array.from(new Set([
  ...materialUses.keys(),
  ...Object.keys(materialFacts),
  ...Object.keys(gaps),
  ...creatureSources.keys(),
])).sort((a, b) => a.localeCompare(b, 'zh-CN'))

export const technologies = Array.from(new Set(recipes.flatMap(recipe => recipe.technology ?? [])))
