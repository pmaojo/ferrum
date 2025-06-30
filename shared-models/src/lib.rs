use serde::{Deserialize, Serialize};
use typeshare::typeshare;

pub mod components;
pub use components::SharedComponent;

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum NodeType {
    UseCase,
    Adapter,
    Port,
    Entity,
    Component,
    Hook,
    Schema,
    Form,
    Validation,
    Upload,
    Policy,
    Resource,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Field {
    pub name: String,
    #[serde(rename = "type")]
    pub field_type: String,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Node {
    pub id: String,
    #[serde(rename = "type")]
    pub node_type: NodeType,
    #[serde(default)]
    pub doc: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub story: Option<String>,
    #[serde(default)]
    pub input: Vec<Field>,
    pub output: Option<String>,
    #[serde(default)]
    pub depends_on: Vec<String>,
    pub implements: Option<String>,
    #[serde(default)]
    pub view: Option<String>,
    #[serde(default)]
    pub schema: Option<String>,
    #[serde(default)]
    pub api_name: Option<String>,
    #[serde(default, rename = "ref")]
    pub ref_node: Option<String>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Module {
    #[serde(rename = "module")]
    pub name: String,
    pub nodes: Vec<Node>,
}

use std::collections::BTreeMap;

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslApp {
    pub name: String,
    #[serde(default)]
    pub title: Option<String>,
    #[serde(default)]
    pub version: Option<String>,
    #[serde(default)]
    pub database: Option<String>,
    #[serde(default)]
    pub features: Vec<String>,
    #[serde(default)]
    pub auth: Option<DslAuth>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslAuth {
    #[serde(rename = "userEntity")]
    pub user_entity: String,
    #[serde(default)]
    pub methods: Vec<String>,
    #[serde(default, rename = "onAuthFailedRedirectTo")]
    pub on_auth_failed_redirect_to: Option<String>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslRoute {
    pub name: String,
    pub path: String,
    pub to: String,
    #[serde(default, rename = "authRequired")]
    pub auth_required: bool,
    #[serde(default)]
    pub policy: Option<String>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslAppPage {
    pub name: String,
    pub component: String,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslCache {
    pub ttl: u32,
    pub key: String,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslQuery {
    pub name: String,
    pub handler: String,
    #[serde(default)]
    pub entities: Vec<String>,
    #[serde(default)]
    pub cache: Option<DslCache>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslMutation {
    pub name: String,
    pub handler: String,
    #[serde(default)]
    pub entities: Vec<String>,
    #[serde(default, rename = "authRequired")]
    pub auth_required: bool,
    #[serde(default)]
    pub policy: Option<String>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslJob {
    pub name: String,
    pub schedule: String,
    pub handler: String,
    #[serde(default)]
    pub policy: Option<String>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslStandaloneEntity {
    pub name: String,
    #[serde(default, rename = "deriveFrom")]
    pub derive_from: Option<String>,
    #[serde(default)]
    pub fields: BTreeMap<String, String>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslStandaloneForm {
    pub name: String,
    #[serde(rename = "submitTo")]
    pub submit_to: String,
    #[serde(default)]
    pub fields: BTreeMap<String, String>,
    #[serde(default)]
    pub policy: Option<String>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslValidation {
    pub name: String,
    #[serde(rename = "appliesTo")]
    pub applies_to: String,
    pub rule: String,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslUpload {
    pub name: String,
    #[serde(default)]
    pub path: String,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslPolicy {
    pub name: String,
    pub guard: String,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslResource {
    pub name: String,
    #[serde(rename = "type")]
    pub resource_type: String,
    #[serde(default)]
    pub config: BTreeMap<String, String>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslForm {
    #[serde(default)]
    pub fields: Vec<String>,
    pub action: String,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum DslStep {
    Ref {
        #[serde(rename = "ref")]
        reference: String,
    },
    Name(String),
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslPage {
    pub route: String,
    #[serde(default)]
    pub component: Option<String>,
    #[serde(default)]
    pub form: Option<DslForm>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslUseCase {
    #[serde(default)]
    pub input: BTreeMap<String, String>,
    pub output: Option<String>,
    #[serde(default)]
    pub doc: Option<String>,
    #[serde(default)]
    pub steps: Vec<DslStep>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslEntity {
    #[serde(default, rename = "deriveFrom")]
    pub derive_from: Option<String>,
    #[serde(default)]
    pub fields: BTreeMap<String, String>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslModule {
    #[serde(default)]
    pub entity: Option<DslEntity>,
    #[serde(default)]
    pub usecases: BTreeMap<String, DslUseCase>,
    #[serde(default)]
    pub pages: BTreeMap<String, DslPage>,
    #[serde(default)]
    pub rpc: BTreeMap<String, DslUseCase>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FerrumDsl {
    pub app: DslApp,
    #[serde(default)]
    pub modules: BTreeMap<String, DslModule>,
    #[serde(default)]
    pub routes: Vec<DslRoute>,
    #[serde(default)]
    pub pages: Vec<DslAppPage>,
    #[serde(default)]
    pub queries: Vec<DslQuery>,
    #[serde(default)]
    pub mutations: Vec<DslMutation>,
    #[serde(default)]
    pub jobs: Vec<DslJob>,
    #[serde(default)]
    pub entities: Vec<DslStandaloneEntity>,
    #[serde(default)]
    pub forms: Vec<DslStandaloneForm>,
    #[serde(default)]
    pub validations: Vec<DslValidation>,
    #[serde(default)]
    pub uploads: Vec<DslUpload>,
    #[serde(default)]
    pub policies: Vec<DslPolicy>,
    #[serde(default)]
    pub resources: Vec<DslResource>,
}
