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
