@tool
extends EditorScenePostImport

func _post_import(scene: Node) -> Node:
	iterate(scene)
	return scene

func iterate(node: Node) -> void:
	if node != null && node is MeshInstance3D:
		var slice_count := node.name.get_slice_count("_");
		node.name = node.name.get_slice("_", slice_count - 1).to_lower();
		print("setting name to: " + node.name)
		
	for child in node.get_children():
		iterate(child)
