use crate::features::expand_features;
use crate::{validator::ValidationResult, Field, Module, Node, NodeType};
use crate::validator::ValidationError;
use ferrum_shared_models::{DslModule, FerrumDsl};
use std::collections::BTreeMap;

/// Convert a [`FerrumDsl`] project into a list of [`Module`] structures.
///
/// This provides a bridge between the higher level YAML DSL and the existing
/// code generation pipeline which operates on `Module` instances.
pub fn project_to_modules(project: &mut FerrumDsl) -> ValidationResult<Vec<Module>> {
    // Collect entity definitions for derive resolution
    let mut entity_defs: BTreeMap<String, (Option<String>, BTreeMap<String, String>)> =
        BTreeMap::new();
    for (name, module) in &project.modules {
        if let Some(ent) = &module.entity {
            entity_defs.insert(name.clone(), (ent.derive_from.clone(), ent.fields.clone()));
        }
    }
    for ent in &project.entities {
        entity_defs.insert(
            ent.name.clone(),
            (ent.derive_from.clone(), ent.fields.clone()),
        );
    }

    fn resolve_fields(
        name: &str,
        defs: &BTreeMap<String, (Option<String>, BTreeMap<String, String>)>,
        cache: &mut BTreeMap<String, BTreeMap<String, String>>,
        stack: &mut Vec<String>,
    ) -> ValidationResult<BTreeMap<String, String>> {
        if let Some(res) = cache.get(name) {
            return Ok(res.clone());
        }
        if stack.contains(&name.to_string()) {
            return Err(ValidationError::CircularEntityDerive {
                entity: name.to_string(),
            });
        }
        if let Some((base, fields)) = defs.get(name) {
            stack.push(name.to_string());
            let mut out = if let Some(b) = base {
                resolve_fields(b, defs, cache, stack)?
            } else {
                BTreeMap::new()
            };
            stack.pop();
            out.extend(fields.clone());
            cache.insert(name.to_string(), out.clone());
            Ok(out)
        } else {
            Ok(BTreeMap::new())
        }
    }

    let mut resolved: BTreeMap<String, BTreeMap<String, String>> = BTreeMap::new();
    for name in entity_defs.keys() {
        resolve_fields(name, &entity_defs, &mut resolved, &mut Vec::new())?;
    }

    let mut modules: Vec<Module> = project
        .modules
        .iter()
        .map(|(name, module)| dsl_module_to_module(name, module, &resolved))
        .collect();

    // Standalone entities outside modules
    for ent in &project.entities {
        let fields = resolved
            .get(&ent.name)
            .cloned()
            .unwrap_or_default()
            .iter()
            .map(|(fname, ftype)| Field {
                name: fname.clone(),
                field_type: ftype.clone(),
            })
            .collect();
        modules.push(Module {
            name: ent.name.clone(),
            nodes: vec![Node {
                id: ent.name.clone(),
                node_type: NodeType::Entity,
                doc: None,
                description: None,
                story: None,
                input: fields,
                output: None,
                depends_on: Vec::new(),
                implements: None,
                view: None,
                schema: None,
                api_name: None,
                ref_node: None,
            }],
        });
    }

    // Standalone forms
    if !project.forms.is_empty() {
        let form_nodes: Vec<Node> = project
            .forms
            .iter()
            .map(|f| {
                let input = f
                    .fields
                    .iter()
                    .map(|(name, ty)| Field {
                        name: name.clone(),
                        field_type: ty.clone(),
                    })
                    .collect();
                Node {
                    id: f.name.clone(),
                    node_type: NodeType::Form,
                    doc: f.policy.clone(),
                    description: Some(f.submit_to.clone()),
                    story: None,
                    input,
                    output: None,
                    depends_on: vec![f.submit_to.clone()],
                    implements: None,
                    view: None,
                    schema: None,
                    api_name: None,
                    ref_node: None,
                }
            })
            .collect();
        modules.push(Module {
            name: "forms".to_string(),
            nodes: form_nodes,
        });
    }

    // Validations
    if !project.validations.is_empty() {
        let val_nodes: Vec<Node> = project
            .validations
            .iter()
            .map(|v| Node {
                id: v.name.clone(),
                node_type: NodeType::Validation,
                doc: None,
                description: Some(v.applies_to.clone()),
                story: Some(v.rule.clone()),
                input: Vec::new(),
                output: None,
                depends_on: Vec::new(),
                implements: None,
                view: None,
                schema: None,
                api_name: None,
                ref_node: None,
            })
            .collect();
        modules.push(Module {
            name: "validations".to_string(),
            nodes: val_nodes,
        });
    }

    // Uploads
    if !project.uploads.is_empty() {
        let upload_nodes: Vec<Node> = project
            .uploads
            .iter()
            .map(|u| Node {
                id: u.name.clone(),
                node_type: NodeType::Upload,
                doc: None,
                description: Some(u.path.clone()),
                story: None,
                input: Vec::new(),
                output: None,
                depends_on: Vec::new(),
                implements: None,
                view: None,
                schema: None,
                api_name: None,
                ref_node: None,
            })
            .collect();
        modules.push(Module {
            name: "uploads".to_string(),
            nodes: upload_nodes,
        });
    }

    if !project.iot.is_empty() {
        let iot_nodes: Vec<Node> = project
            .iot
            .iter()
            .map(|i| Node {
                id: i.name.clone(),
                node_type: NodeType::Iot,
                doc: None,
                description: None,
                story: None,
                input: Vec::new(),
                output: None,
                depends_on: Vec::new(),
                implements: None,
                view: None,
                schema: None,
                api_name: None,
                ref_node: None,
            })
            .collect();
        modules.push(Module {
            name: "iot".to_string(),
            nodes: iot_nodes,
        });
    }

    expand_features(project, &mut modules);
    Ok(modules)
}

/// Convert a single [`DslModule`] into a [`Module`].
fn dsl_module_to_module(
    name: &str,
    module: &DslModule,
    resolved: &BTreeMap<String, BTreeMap<String, String>>,
) -> Module {
    let mut nodes = Vec::new();

    // Entity
    if let Some(entity) = &module.entity {
        let fields_map = resolved
            .get(name)
            .cloned()
            .unwrap_or_else(|| entity.fields.clone());
        let fields = fields_map
            .iter()
            .map(|(fname, ftype)| Field {
                name: fname.clone(),
                field_type: ftype.clone(),
            })
            .collect();
        nodes.push(Node {
            id: name.to_string(),
            node_type: NodeType::Entity,
            doc: None,
            description: None,
            story: None,
            input: fields,
            output: None,
            depends_on: Vec::new(),
            implements: None,
            view: None,
            schema: None,
            api_name: None,
            ref_node: None,
        });
    }

    // Use cases
    for (uc_name, uc) in &module.usecases {
        let input = uc
            .input
            .iter()
            .map(|(fname, ftype)| Field {
                name: fname.clone(),
                field_type: ftype.clone(),
            })
            .collect();

        nodes.push(Node {
            id: uc_name.clone(),
            node_type: NodeType::UseCase,
            doc: uc.doc.clone(),
            description: None,
            story: None,
            input,
            output: uc.output.clone(),
            depends_on: uc
                .steps
                .iter()
                .map(|s| match s {
                    ferrum_shared_models::DslStep::Ref { reference } => reference.clone(),
                    ferrum_shared_models::DslStep::Name(n) => n.clone(),
                })
                .collect(),
            implements: None,
            view: None,
            schema: None,
            api_name: None,
            ref_node: None,
        });
    }

    // RPC -- treated as use cases for now
    for (rpc_name, rpc) in &module.rpc {
        let input = rpc
            .input
            .iter()
            .map(|(fname, ftype)| Field {
                name: fname.clone(),
                field_type: ftype.clone(),
            })
            .collect();

        nodes.push(Node {
            id: rpc_name.clone(),
            node_type: NodeType::UseCase,
            doc: rpc.doc.clone(),
            description: None,
            story: None,
            input,
            output: rpc.output.clone(),
            depends_on: rpc
                .steps
                .iter()
                .map(|s| match s {
                    ferrum_shared_models::DslStep::Ref { reference } => reference.clone(),
                    ferrum_shared_models::DslStep::Name(n) => n.clone(),
                })
                .collect(),
            implements: None,
            view: None,
            schema: None,
            api_name: None,
            ref_node: None,
        });
    }

    // Pages -> basic components
    for (page_name, page) in &module.pages {
        nodes.push(Node {
            id: page_name.clone(),
            node_type: NodeType::Component,
            doc: None,
            description: Some(page.route.clone()),
            story: None,
            input: Vec::new(),
            output: None,
            depends_on: Vec::new(),
            implements: None,
            view: page.component.clone(),
            schema: None,
            api_name: None,
            ref_node: None,
        });
    }

    Module {
        name: name.to_string(),
        nodes,
    }
}
