import 'dart:convert';
import 'package:http/http.dart' as http;

/// Thin REST client for the Alkathiry Odoo gateway.
///
/// Every screen is rendered from the JSON these calls return, so the client
/// only moves untyped maps around — no generated models, keeping the codebase
/// compatible with on-device compilation (AIDE / Android IDE).
class ApiClient {
  ApiClient({required this.baseUrl});

  /// e.g. http://10.0.2.2:8069 for the Android emulator hitting local Odoo.
  final String baseUrl;
  String? _accessToken;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_accessToken != null) 'Authorization': 'Bearer $_accessToken',
      };

  Uri _u(String path) => Uri.parse('$baseUrl/api/v1$path');

  Future<Map<String, dynamic>> _unwrap(http.Response r) async {
    final body = jsonDecode(r.body) as Map<String, dynamic>;
    if (body['success'] != true) {
      final err = body['error'] ?? {'message': 'Request failed'};
      throw ApiException(err['code']?.toString() ?? 'ERROR', err['message']?.toString() ?? '');
    }
    return (body['data'] as Map<String, dynamic>?) ?? {};
  }

  // ---- Auth ----
  Future<String> requestOtp(String phone) async {
    final r = await http.post(_u('/auth/request-otp'),
        headers: _headers, body: jsonEncode({'phone': phone}));
    final data = await _unwrap(r);
    return data['token_uid'] as String;
  }

  Future<Map<String, dynamic>> verifyOtp(String tokenUid, String otp) async {
    final r = await http.post(_u('/auth/verify-otp'),
        headers: _headers, body: jsonEncode({'token_uid': tokenUid, 'otp': otp}));
    final data = await _unwrap(r);
    _accessToken = data['access_token'] as String?;
    return data;
  }

  // ---- Metadata ----
  Future<List<dynamic>> registrationSchema() async {
    final r = await http.get(_u('/meta/registration'), headers: _headers);
    final data = await _unwrap(r);
    return (data['categories'] as List<dynamic>?) ?? [];
  }

  // ---- Beneficiary ----
  Future<Map<String, dynamic>> me() async =>
      _unwrap(await http.get(_u('/me'), headers: _headers));

  Future<List<dynamic>> myServices() async {
    final data = await _unwrap(await http.get(_u('/me/services'), headers: _headers));
    return (data['services'] as List<dynamic>?) ?? [];
  }

  Future<Map<String, dynamic>> barcode() async =>
      _unwrap(await http.get(_u('/me/barcode'), headers: _headers));

  // ---- Distributor loop ----
  Future<Map<String, dynamic>> scan(String barcode, int allocationId, double qty) async {
    final r = await http.post(_u('/distributor/scan'),
        headers: _headers,
        body: jsonEncode({'barcode': barcode, 'allocation_id': allocationId, 'quantity': qty}));
    return _unwrap(r);
  }

  Future<Map<String, dynamic>> confirm(
      String otpTokenUid, String otp, int allocationId, double qty) async {
    final r = await http.post(_u('/distributor/confirm'),
        headers: _headers,
        body: jsonEncode({
          'otp_token_uid': otpTokenUid,
          'otp': otp,
          'allocation_id': allocationId,
          'quantity': qty,
        }));
    return _unwrap(r);
  }
}

class ApiException implements Exception {
  ApiException(this.code, this.message);
  final String code;
  final String message;
  @override
  String toString() => '[$code] $message';
}
