import 'package:flutter/material.dart';

/// Builds a form at runtime from a list of JSON field descriptors returned by
/// the Odoo backend (`GET /api/v1/meta/registration`). Adding, removing or
/// reordering fields in the Odoo Admin UI changes the rendered form with no app
/// code change — the Absolute Dynamism mandate applied to the mobile layer.
///
/// Each descriptor looks like:
/// { "key", "label", "type", "required", "options":[{value,label}], "placeholder" }
class DynamicForm extends StatefulWidget {
  const DynamicForm({super.key, required this.fields, required this.onSubmit});

  final List<dynamic> fields;
  final void Function(Map<String, dynamic> values) onSubmit;

  @override
  State<DynamicForm> createState() => _DynamicFormState();
}

class _DynamicFormState extends State<DynamicForm> {
  final _formKey = GlobalKey<FormState>();
  final Map<String, dynamic> _values = {};

  @override
  Widget build(BuildContext context) {
    final sorted = List<dynamic>.from(widget.fields)
      ..sort((a, b) => (a['sequence'] ?? 0).compareTo(b['sequence'] ?? 0));
    return Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          ...sorted.map(_buildField),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: () {
              if (_formKey.currentState!.validate()) {
                _formKey.currentState!.save();
                widget.onSubmit(_values);
              }
            },
            child: const Text('Submit'),
          ),
        ],
      ),
    );
  }

  Widget _buildField(dynamic f) {
    final key = f['key'] as String;
    final type = f['type'] as String? ?? 'char';
    final label = f['label'] as String? ?? key;
    final required = f['required'] == true;

    String? req(String? v) =>
        (required && (v == null || v.isEmpty)) ? 'Required' : null;

    switch (type) {
      case 'boolean':
        return SwitchListTile(
          title: Text(label),
          value: _values[key] == true,
          onChanged: (v) => setState(() => _values[key] = v),
        );
      case 'selection':
      case 'multiselect':
        final options = (f['options'] as List<dynamic>?) ?? [];
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: DropdownButtonFormField<dynamic>(
            decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
            items: options
                .map((o) => DropdownMenuItem(
                      value: o['value'],
                      child: Text(o['label']?.toString() ?? o['value'].toString()),
                    ))
                .toList(),
            validator: (v) => (required && v == null) ? 'Required' : null,
            onChanged: (v) => _values[key] = v,
            onSaved: (v) => _values[key] = v,
          ),
        );
      case 'document':
      case 'image':
        // Upload slot placeholder — wired to a file/camera picker on device.
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: OutlinedButton.icon(
            icon: const Icon(Icons.upload_file),
            label: Text('Upload: $label'),
            onPressed: () => _values[key] = 'PENDING_UPLOAD',
          ),
        );
      default:
        final keyboard = (type == 'integer' || type == 'float')
            ? TextInputType.number
            : (type == 'date' ? TextInputType.datetime : TextInputType.text);
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: TextFormField(
            decoration: InputDecoration(
              labelText: label + (required ? ' *' : ''),
              hintText: f['placeholder']?.toString(),
              helperText: f['help']?.toString(),
              border: const OutlineInputBorder(),
            ),
            keyboardType: keyboard,
            maxLines: type == 'text' ? 4 : 1,
            validator: req,
            onSaved: (v) => _values[key] = v,
          ),
        );
    }
  }
}
