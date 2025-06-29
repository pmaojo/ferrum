use serde::{Deserialize, Serialize};
use typeshare::typeshare;

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
    pub database: Option<String>,
    #[serde(default)]
    pub features: Vec<String>,
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
    pub steps: Vec<String>,
}

#[typeshare]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DslEntity {
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
}
