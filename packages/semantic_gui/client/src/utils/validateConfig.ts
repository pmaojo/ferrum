import Ajv, { ErrorObject } from 'ajv';

export interface ValidationResult {
  isValid: boolean;
  errors: Record<string, string>;
}

export function validateConfig<
  S extends Record<string, unknown>,
  D extends Record<string, unknown>
>(schema: S, data: D): ValidationResult {
  const ajv = new Ajv({ allErrors: true, useDefaults: true });
  const validate = ajv.compile(schema);
  const valid = validate(data);

  const errors: Record<string, string> = {};
  if (!valid && validate.errors) {
    for (const err of validate.errors as ErrorObject[]) {
      let field = err.instancePath.replace(/^\//, '');
      if (!field && err.keyword === 'required') {
        const missingProperty = (err.params as Record<string, unknown>)[
          'missingProperty'
        ];
        if (typeof missingProperty === 'string') {
          field = missingProperty;
          errors[field] = 'This field is required';
        }
      } else if (field) {
        errors[field] = err.message || 'Invalid value';
      }
    }
  }

  return { isValid: Boolean(valid), errors };
}
