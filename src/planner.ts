import { gaps, recipeForItem } from './catalog'
import type { Ingredient, Recipe } from './catalog'

export type Inventory = Record<string, number>

export interface PlanNode {
  item: string
  quantity: number
  fromBag: number
  batches?: number
  missing?: number
  reason?: string
  recipe?: Recipe
  children: PlanNode[]
}

export function findMissing(recipe: Recipe, inventory: Inventory, batches = 1) {
  return recipe.ingredients?.flatMap(({ item, quantity }) => {
    const missing = quantity * batches - (inventory[item] ?? 0)
    return missing > 0 ? [{ item, quantity: missing }] : []
  }) ?? []
}

export function planRecipe(recipe: Recipe, batches: number, inventory: Inventory) {
  if (!recipe.ingredients) return null

  const available = new Map(Object.entries(inventory))
  const shortages = new Map<string, number>()
  const requiredTechnology = new Set(recipe.technology ?? [])
  let unknownTechnology = recipe.kind === 'craft' && !recipe.technology

  function expand({ item, quantity }: Ingredient, path: Set<string>): PlanNode {
    const stock = available.get(item) ?? 0
    const fromBag = Math.min(stock, quantity)
    available.set(item, stock - fromBag)
    const missing = quantity - fromBag
    const node: PlanNode = { item, quantity, fromBag, children: [] }
    if (!missing) return node

    const child = recipeForItem.get(item)
    if (child?.ingredients && child.output && !path.has(item)) {
      node.recipe = child
      const childBatches = Math.ceil(missing / child.output)
      node.batches = childBatches
      const childPath = new Set([...path, item])
      child.technology?.forEach(technology => requiredTechnology.add(technology))
      unknownTechnology ||= child.kind === 'craft' && !child.technology
      node.children = child.ingredients.map(ingredient =>
        expand({ ...ingredient, quantity: ingredient.quantity * childBatches }, childPath))
      const surplus = childBatches * child.output - missing
      available.set(item, (available.get(item) ?? 0) + surplus)
      return node
    }

    node.missing = missing
    node.recipe = child
    if (path.has(item)) node.reason = '检测到循环配方'
    else if (child?.ingredients) node.reason = '单次产量待核实'
    else if (child) node.reason = '用量待核实'
    else if (Object.hasOwn(gaps, item)) node.reason = 'Wiki 未列具体配方'
    else node.reason = '未收录制作配方'
    shortages.set(item, (shortages.get(item) ?? 0) + missing)
    return node
  }

  const tree = recipe.ingredients.map(ingredient =>
    expand({ ...ingredient, quantity: ingredient.quantity * batches }, new Set([recipe.name])))
  const missing = Array.from(shortages, ([item, quantity]) => ({ item, quantity }))
  return { tree, missing, requiredTechnology: [...requiredTechnology], unknownTechnology }
}
