import 'package:flutter/material.dart';

import 'api_client.dart';
import 'dynamic_form.dart';

/// Point this at your Odoo gateway. 10.0.2.2 = host loopback from the Android
/// emulator; use the LAN IP for a physical device.
const String kBaseUrl = 'http://10.0.2.2:8069';

void main() => runApp(const AlkathiryApp());

class AlkathiryApp extends StatelessWidget {
  const AlkathiryApp({super.key});

  @override
  Widget build(BuildContext context) {
    final api = ApiClient(baseUrl: kBaseUrl);
    return MaterialApp(
      title: 'Alkathiry',
      theme: ThemeData(colorSchemeSeed: Colors.teal, useMaterial3: true),
      home: HomeHub(api: api),
    );
  }
}

/// Simple role hub so one build serves Beneficiary, Distributor and the dynamic
/// registration flow. In production the role is derived from the session.
class HomeHub extends StatelessWidget {
  const HomeHub({super.key, required this.api});
  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Alkathiry')),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            FilledButton(
              onPressed: () => Navigator.push(context,
                  MaterialPageRoute(builder: (_) => RegistrationScreen(api: api))),
              child: const Text('Register (Beneficiary)'),
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: () => Navigator.push(context,
                  MaterialPageRoute(builder: (_) => LoginScreen(api: api))),
              child: const Text('Login'),
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: () => Navigator.push(context,
                  MaterialPageRoute(builder: (_) => DistributorScreen(api: api))),
              child: const Text('Distributor Console'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Renders the registration form purely from backend metadata.
class RegistrationScreen extends StatelessWidget {
  const RegistrationScreen({super.key, required this.api});
  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Register')),
      body: FutureBuilder<List<dynamic>>(
        future: api.registrationSchema(),
        builder: (context, snap) {
          if (!snap.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final categories = snap.data!;
          if (categories.isEmpty) {
            return const Center(child: Text('No categories configured.'));
          }
          final fields = (categories.first['fields'] as List<dynamic>?) ?? [];
          return DynamicForm(
            fields: fields,
            onSubmit: (values) => ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Captured ${values.length} fields (demo).')),
            ),
          );
        },
      ),
    );
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.api});
  final ApiClient api;
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _phone = TextEditingController();
  final _otp = TextEditingController();
  String? _tokenUid;
  String _msg = '';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Login')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          TextField(controller: _phone, decoration: const InputDecoration(labelText: 'Phone')),
          if (_tokenUid != null)
            TextField(controller: _otp, decoration: const InputDecoration(labelText: 'OTP')),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: () async {
              try {
                if (_tokenUid == null) {
                  final t = await widget.api.requestOtp(_phone.text);
                  setState(() => _tokenUid = t);
                } else {
                  await widget.api.verifyOtp(_tokenUid!, _otp.text);
                  if (mounted) {
                    Navigator.pushReplacement(context,
                        MaterialPageRoute(builder: (_) => BeneficiaryHome(api: widget.api)));
                  }
                }
              } catch (e) {
                setState(() => _msg = e.toString());
              }
            },
            child: Text(_tokenUid == null ? 'Request OTP' : 'Verify'),
          ),
          Text(_msg, style: const TextStyle(color: Colors.red)),
        ]),
      ),
    );
  }
}

class BeneficiaryHome extends StatelessWidget {
  const BeneficiaryHome({super.key, required this.api});
  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My Services')),
      body: FutureBuilder<List<dynamic>>(
        future: api.myServices(),
        builder: (context, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final services = snap.data!;
          return Column(children: [
            // Targeted ad banners — served independently of service execution.
            FutureBuilder<List<dynamic>>(
              future: api.ads('beneficiary_home'),
              builder: (context, adSnap) {
                final ads = adSnap.data ?? [];
                if (ads.isEmpty) return const SizedBox.shrink();
                return SizedBox(
                  height: 90,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: ads
                        .map((a) => Card(
                              color: Colors.amber.shade100,
                              child: Padding(
                                padding: const EdgeInsets.all(12),
                                child: Center(child: Text(a['title']?.toString() ?? '')),
                              ),
                            ))
                        .toList(),
                  ),
                );
              },
            ),
            Expanded(
              child: ListView(
                children: services
                    .map((s) => ListTile(
                          title: Text(s['service']?.toString() ?? ''),
                          subtitle: Text('Model ${s['distribution_model']}'),
                          trailing: Text('${s['remaining']}/${s['quota']}'),
                        ))
                    .toList(),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: FilledButton.icon(
                icon: const Icon(Icons.qr_code),
                label: const Text('Show my barcode'),
                onPressed: () async {
                  final b = await api.barcode();
                  if (context.mounted) _showBarcode(context, b);
                },
              ),
            ),
          ]);
        },
      ),
    );
  }

  void _showBarcode(BuildContext context, Map<String, dynamic> b) {
    // The token string is what the distributor scans. A QR widget (qr_flutter)
    // can render it visually on a desktop build; here we show the payload.
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: Text('Barcode (expires in ${b['expires_in']}s)'),
        content: SelectableText(b['token']?.toString() ?? ''),
      ),
    );
  }
}

/// Distributor side of Sequence Diagram 26.1: scan → (OTP) → confirm.
class DistributorScreen extends StatefulWidget {
  const DistributorScreen({super.key, required this.api});
  final ApiClient api;
  @override
  State<DistributorScreen> createState() => _DistributorScreenState();
}

class _DistributorScreenState extends State<DistributorScreen> {
  final _barcode = TextEditingController();
  final _allocation = TextEditingController();
  final _otp = TextEditingController();
  String? _otpTokenUid;
  String _msg = '';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Distributor')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          // Camera scanning uses mobile_scanner on a full build; manual entry
          // keeps this foundation plugin-free for on-device compilation.
          TextField(controller: _barcode, decoration: const InputDecoration(labelText: 'Scanned barcode token')),
          TextField(controller: _allocation, decoration: const InputDecoration(labelText: 'Allocation ID')),
          if (_otpTokenUid != null)
            TextField(controller: _otp, decoration: const InputDecoration(labelText: 'Beneficiary OTP')),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: _otpTokenUid == null ? _scan : _confirm,
            child: Text(_otpTokenUid == null ? 'Scan & Validate' : 'Confirm Redemption'),
          ),
          const SizedBox(height: 12),
          Text(_msg),
        ]),
      ),
    );
  }

  Future<void> _scan() async {
    try {
      final r = await widget.api
          .scan(_barcode.text, int.tryParse(_allocation.text) ?? 0, 1);
      if (r['eligible'] == true) {
        setState(() {
          _otpTokenUid = r['otp_token_uid'] as String?;
          _msg = 'Eligible — OTP sent to beneficiary.';
        });
      } else {
        final failed = (r['verdict']?['failed'] as List<dynamic>?) ?? [];
        setState(() => _msg = 'Not eligible: ${failed.join(", ")}');
      }
    } catch (e) {
      setState(() => _msg = e.toString());
    }
  }

  Future<void> _confirm() async {
    try {
      final r = await widget.api
          .confirm(_otpTokenUid!, _otp.text, int.tryParse(_allocation.text) ?? 0, 1);
      setState(() {
        _msg = r['confirmed'] == true
            ? 'Confirmed: ${r['transaction_number']}'
            : 'Failed.';
        if (r['confirmed'] == true) _otpTokenUid = null;
      });
    } catch (e) {
      setState(() => _msg = e.toString());
    }
  }
}
