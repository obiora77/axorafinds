import type { TypedSchema } from 'vee-validate'
import type { z } from 'zod'

/**
 * Small adapter so vee-validate can use a zod schema directly.
 * (vee-validate 4.15 has no built-in zod support and the brief lists only vee-validate + zod.)
 */
export function toFormSchema<S extends z.ZodType>(schema: S): TypedSchema<z.input<S>, z.output<S>> {
  return {
    __type: 'VVTypedSchema',
    async parse(values) {
      const result = await schema.safeParseAsync(values)
      if (result.success) return { value: result.data, errors: [] }

      const grouped: Record<string, string[]> = {}
      for (const issue of result.error.issues) {
        const path = issue.path.map(String).join('.')
        ;(grouped[path] ||= []).push(issue.message)
      }
      return { errors: Object.entries(grouped).map(([path, errors]) => ({ path, errors })) }
    },
  }
}
