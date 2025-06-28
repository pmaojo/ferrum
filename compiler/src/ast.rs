use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum NodeType {
    UseCase,
    Adapter,
    Port,
    Entity,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Field {
    pub name: String,
    #[serde(rename = "type")]
    pub field_type: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Node {
    pub id: String,
    #[serde(rename = "type")]
    pub node_type: NodeType,
    #[serde(default)]
    pub input: Vec<Field>,
    pub output: Option<String>,
    #[serde(default)]
    pub depends_on: Vec<String>,
    pub implements: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Module {
    #[serde(rename = "module")]
    pub name: String,
    pub nodes: Vec<Node>,
}
