use crate::features::expand_features;
use crate::{Field, Module, Node, NodeType};
use ferrum_shared_models::{DslModule, FerrumDsl};

/// Convert a [`FerrumDsl`] project into a list of [`Module`] structures.
///
/// This provides a bridge between the higher level YAML DSL and the existing
/// code generation pipeline which operates on `Module` instances.
pub fn project_to_modules(project: &FerrumDsl) -> Vec<Module> {
    let mut modules: Vec<Module> = project
        .modules
        .iter()
        .map(|(name, module)| dsl_module_to_module(name, module))
        .collect();

    // Standalone entities outside modules
    for ent in &project.entities {
        let fields = ent
            .fields
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
                description: None,
                story: None,
                input: fields,
                output: None,
                depends_on: Vec::new(),
                implements: None,
                view: None,
                schema: None,
                api_name: None,
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
                    description: Some(f.submit_to.clone()),
                    story: None,
                    input,
                    output: None,
                    depends_on: vec![f.submit_to.clone()],
                    implements: None,
                    view: None,
                    schema: None,
                    api_name: None,
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
                description: Some(v.applies_to.clone()),
                story: Some(v.rule.clone()),
                input: Vec::new(),
                output: None,
                depends_on: Vec::new(),
                implements: None,
                view: None,
                schema: None,
                api_name: None,
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
                description: Some(u.path.clone()),
                story: None,
                input: Vec::new(),
                output: None,
                depends_on: Vec::new(),
                implements: None,
                view: None,
                schema: None,
                api_name: None,
            })
            .collect();
        modules.push(Module {
            name: "uploads".to_string(),
            nodes: upload_nodes,
        });
    }

    expand_features(project, &mut modules);
    modules
}

/// Convert a single [`DslModule`] into a [`Module`].
fn dsl_module_to_module(name: &str, module: &DslModule) -> Module {
    let mut nodes = Vec::new();

    // Entity
    if let Some(entity) = &module.entity {
        let fields = entity
            .fields
            .iter()
            .map(|(fname, ftype)| Field {
                name: fname.clone(),
                field_type: ftype.clone(),
            })
            .collect();
        nodes.push(Node {
            id: name.to_string(),
            node_type: NodeType::Entity,
            description: None,
            story: None,
            input: fields,
            output: None,
            depends_on: Vec::new(),
            implements: None,
            view: None,
            schema: None,
            api_name: None,
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
            description: None,
            story: None,
            input,
            output: uc.output.clone(),
            depends_on: uc.steps.clone(),
            implements: None,
            view: None,
            schema: None,
            api_name: None,
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
            description: None,
            story: None,
            input,
            output: rpc.output.clone(),
            depends_on: rpc.steps.clone(),
            implements: None,
            view: None,
            schema: None,
            api_name: None,
        });
    }

    // Pages -> basic components
    for (page_name, page) in &module.pages {
        nodes.push(Node {
            id: page_name.clone(),
            node_type: NodeType::Component,
            description: Some(page.route.clone()),
            story: None,
            input: Vec::new(),
            output: None,
            depends_on: Vec::new(),
            implements: None,
            view: page.component.clone(),
            schema: None,
            api_name: None,
        });
    }

    Module {
        name: name.to_string(),
        nodes,
    }
}
