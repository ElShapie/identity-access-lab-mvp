import 'package:flutter/material.dart';
import '../services/frigate_api_service.dart';

class MobileShiftScreen extends StatefulWidget {
  final FrigateApiService apiService;

  const MobileShiftScreen({Key? key, required this.apiService}) : super(key: key);

  @override
  State<MobileShiftScreen> createState() => _MobileShiftScreenState();
}

class _MobileShiftScreenState extends State<MobileShiftScreen> {
  final _formKey = GlobalKey<FormState>();
  final _operatorController = TextEditingController(text: 'Guardia Móvil');
  final _notesController = TextEditingController();

  String _selectedShift = 'tarde';
  String _selectedStatus = 'success';
  bool _cam1Checked = true;
  bool _cam2Checked = true;
  bool _isSubmitting = false;

  @override
  void dispose() {
    _operatorController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _submitHandover() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSubmitting = true);

    final verifiedCams = <String>[];
    if (_cam1Checked) verifiedCams.add('Cámara 1 (Entrada)');
    if (_cam2Checked) verifiedCams.add('Cámara 2 (Interior)');

    final success = await widget.apiService.submitShiftHandover(
      operatorName: _operatorController.text.trim(),
      shift: _selectedShift,
      status: _selectedStatus,
      notes: _notesController.text.trim(),
      verifiedCameras: verifiedCams,
    );

    setState(() => _isSubmitting = false);

    if (!mounted) return;

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Relevo de guardia asentado en bitácora central.'),
          backgroundColor: Colors.green,
        ),
      );
      _notesController.clear();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Guardado localmente. Sin conexión al backend Flask.'),
          backgroundColor: Colors.orange,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Relevo de Guardia SOC'),
        backgroundColor: const Color(0xFF1E293B),
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Encabezado
              const Text(
                'Registro de Turno Móvil',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 4),
              Text(
                'Formalización de responsabilidades y flujo de cámaras en sitio.',
                style: TextStyle(color: Colors.grey[600], fontSize: 13),
              ),
              const SizedBox(height: 20),

              // Operador
              TextFormField(
                controller: _operatorController,
                decoration: const InputDecoration(
                  labelText: 'Operador / Guardia a Cargo',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.badge_outlined),
                ),
                validator: (val) => val == null || val.isEmpty ? 'Campo obligatorio' : null,
              ),
              const SizedBox(height: 16),

              // Turno
              DropdownButtonFormField<String>(
                value: _selectedShift,
                decoration: const InputDecoration(
                  labelText: 'Turno',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.schedule),
                ),
                items: const [
                  DropdownMenuItem(value: 'mañana', child: Text('Mañana (06:00 - 14:00)')),
                  DropdownMenuItem(value: 'tarde', child: Text('Tarde (14:00 - 22:00)')),
                  DropdownMenuItem(value: 'noche', child: Text('Noche (22:00 - 06:00)')),
                ],
                onChanged: (val) => setState(() => _selectedShift = val!),
              ),
              const SizedBox(height: 16),

              // Verificación de Cámaras
              const Text(
                'Verificación de Cámaras en App Móvil',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
              const SizedBox(height: 8),
              CheckboxListTile(
                value: _cam1Checked,
                title: const Text('Cámara 1 (Entrada / Torniquete)'),
                subtitle: const Text('Feed de verificación visual de accesos'),
                onChanged: (val) => setState(() => _cam1Checked = val ?? false),
              ),
              CheckboxListTile(
                value: _cam2Checked,
                title: const Text('Cámara 2 (Interior / Hall)'),
                subtitle: const Text('Feed de pasillo y sala de espera'),
                onChanged: (val) => setState(() => _cam2Checked = val ?? false),
              ),
              const SizedBox(height: 16),

              // Diagnóstico
              DropdownButtonFormField<String>(
                value: _selectedStatus,
                decoration: const InputDecoration(
                  labelText: 'Diagnóstico Operativo',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.shield_outlined),
                ),
                items: const [
                  DropdownMenuItem(value: 'success', child: Text('● Conforme (Sin incidencias)')),
                  DropdownMenuItem(value: 'warning', child: Text('● Advertencia (Novedades menores)')),
                  DropdownMenuItem(value: 'danger', child: Text('● Peligro / Incidencia crítica')),
                ],
                onChanged: (val) => setState(() => _selectedStatus = val!),
              ),
              const SizedBox(height: 16),

              // Novedades
              TextFormField(
                controller: _notesController,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: 'Novedades y Bitácora del Turno',
                  hintText: 'Detalles de accesos denegados, novedades de rondines o cámaras...',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 24),

              // Botón guardar
              SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton.icon(
                  onPressed: _isSubmitting ? null : _submitHandover,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF146EF5),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  icon: _isSubmitting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                        )
                      : const Icon(Icons.save),
                  label: Text(_isSubmitting ? 'Guardando...' : 'Asentar Relevo en Bitácora'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
