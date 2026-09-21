use crate::{Module, Node};
use serde::Serialize;

/// Metadata about validation functions used by a use case.
#[derive(Serialize)]
pub struct FieldValidation {
    pub field: String,
    pub func: String,
}

/// Context passed to usecase templates.
#[derive(Serialize)]
pub struct UsecaseContext<'a> {
    pub module: &'a Module,
    pub node: &'a Node,
    pub module_name: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub field_validations: Option<Vec<FieldValidation>>,
}

/// Context for adapters.
#[derive(Serialize)]
pub struct AdapterContext<'a> {
    pub module: &'a Module,
    pub node: &'a Node,
    pub module_name: &'a str,
}

/// Context for ports.
#[derive(Serialize)]
pub struct PortContext<'a> {
    pub module: &'a Module,
    pub node: &'a Node,
    pub module_name: &'a str,
}

/// Context for entities.
#[derive(Serialize)]
pub struct EntityContext<'a> {
    pub module: &'a Module,
    pub node: &'a Node,
    pub module_name: &'a str,
    pub fields: Vec<DieselField>,
}

/// Context for components.
#[derive(Serialize)]
pub struct ComponentContext<'a> {
    pub module: &'a Module,
    pub node: &'a Node,
    pub module_name: &'a str,
}

/// Context for hooks.
#[derive(Serialize)]
pub struct HookContext<'a> {
    pub module: &'a Module,
    pub node: &'a Node,
    pub module_name: &'a str,
}

/// Context for schemas.
#[derive(Serialize)]
pub struct SchemaContext<'a> {
    pub module: &'a Module,
    pub node: &'a Node,
    pub module_name: &'a str,
}

/// Context for forms.
#[derive(Serialize)]
pub struct FormContext<'a> {
    pub module: &'a Module,
    pub node: &'a Node,
    /// PascalCase name of the mutation hook this form submits to (from
    /// `node.description`, i.e. the DSL's `submitTo`), computed with the
    /// same `to_pascal_case()` the mutation generator itself uses so the
    /// import always matches the file that generator actually writes.
    pub hook_name: String,
    /// PascalCase name of an optional policy-gate hook (from `node.doc`).
    pub policy_hook_name: Option<String>,
}

/// Parsed validation rule used when generating validation functions.
#[derive(Debug, Serialize, Clone)]
pub struct ParsedRule {
    pub kind: String,
    pub pattern: Option<String>,
    pub min: Option<i32>,
    pub max: Option<i32>,
}

/// Context for validation templates.
#[derive(Serialize)]
pub struct ValidationContext<'a> {
    pub module: &'a Module,
    pub node: &'a Node,
    pub rule: ParsedRule,
    pub fn_name: String,
}

/// Context for uploads.
#[derive(Serialize)]
pub struct UploadContext<'a> {
    pub module: &'a Module,
    pub node: &'a Node,
}

/// Context for optional batteries (e.g. auth).
#[derive(Serialize)]
pub struct BatteriesContext<'a> {
    pub module: &'a Module,
    pub module_name: &'a str,
}

/// Context for documentation templates.
#[derive(Serialize)]
pub struct DocumentationContext<'a> {
    pub module: &'a Module,
    pub node: &'a Node,
}

/// Field metadata used in Diesel ORM templates.
#[derive(Serialize, Clone)]
pub struct DieselField {
    pub name: String,
    pub rust_type: String,
    pub sql_type: String,
}

/// Context for Diesel ORM templates.
#[derive(Serialize)]
pub struct DieselContext {
    pub table_name: String,
    pub struct_name: String,
    pub fields: Vec<DieselField>,
}
