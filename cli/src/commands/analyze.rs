use anyhow::Result;
use std::path::PathBuf;

pub fn analyze(file: PathBuf, json: bool, bottleneck: usize) -> Result<()> {
    let mut dsl = ferrum_compiler::parse_dsl_yaml(&file)?;
    let modules = ferrum_compiler::project_to_modules(&mut dsl);
    let graph = ferrum_compiler::build_graph(&modules);
    let layers = ferrum_compiler::classify_layers(&modules);
    let cycles = ferrum_compiler::find_cycles(&graph);
    let bottlenecks = ferrum_compiler::find_bottlenecks(&graph, bottleneck);
    if json {
        let out = serde_json::json!({
            "cycles": cycles,
            "bottlenecks": bottlenecks,
            "layers": layers,
        });
        println!("{}", serde_json::to_string_pretty(&out)?);
    } else {
        if cycles.is_empty() {
            println!("✅ No dependency cycles detected");
        } else {
            println!("⚠️ Found {} cycle(s):", cycles.len());
            for c in cycles {
                println!("  - {}", c.join(" -> "));
            }
        }
        if bottlenecks.is_empty() {
            println!("✅ No bottlenecks detected");
        } else {
            println!("⚠️ Potential bottlenecks: {}", bottlenecks.join(", "));
        }
        println!("Layers:");
        for (layer, nodes) in layers {
            println!("  - {:?}: {} node(s)", layer, nodes.len());
        }
    }
    Ok(())
}

