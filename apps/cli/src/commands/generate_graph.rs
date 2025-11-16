use anyhow::Result;
use std::path::PathBuf;

pub fn generate_graph(file: PathBuf, output: PathBuf) -> Result<()> {
    use std::fs;

    let module = ferrum_compiler::parse_yaml(&file)?;
    let mut dot = String::from("digraph Ferrum {\n");
    for node in &module.nodes {
        dot.push_str(&format!(
            "    {} [label=\"{} ({:?})\"];\n",
            node.id, node.id, node.node_type
        ));
        for dep in &node.depends_on {
            dot.push_str(&format!("    {} -> {};\n", node.id, dep));
        }
    }
    dot.push_str("}\n");
    fs::write(&output, dot)?;
    println!("✅ Graph written to {}", output.display());
    Ok(())
}

