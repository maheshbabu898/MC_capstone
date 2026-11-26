import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  ApiClient._();

  static const String _defaultUrl = String.fromEnvironment(
    'MEC_API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );
  static String baseUrl = _defaultUrl;

  static Future<void> loadSettings() async {
    final preferences = await SharedPreferences.getInstance();
    baseUrl = preferences.getString('api_base_url') ?? _defaultUrl;
  }

  static Future<void> saveBaseUrl(String value) async {
    final normalized = value.trim().replaceAll(RegExp(r'/+$'), '');
    final uri = Uri.tryParse(normalized);
    if (uri == null || !uri.hasScheme || uri.host.isEmpty) {
      throw const FormatException('Enter a complete backend URL, including http:// or https://.');
    }
    baseUrl = normalized;
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString('api_base_url', normalized);
  }

  static Future<dynamic> get(String path) async {
    final response = await http.get(Uri.parse('$baseUrl$path')).timeout(
          const Duration(seconds: 15),
        );
    return _decode(response);
  }

  static Future<dynamic> post(String path, Map<String, dynamic> body) async {
    final response = await http
        .post(
          Uri.parse('$baseUrl$path'),
          headers: const {'Content-Type': 'application/json'},
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 180));
    return _decode(response);
  }

  static Future<dynamic> upload(
    PlatformFile file,
    String taskType,
    double cpuCyclesGiga,
  ) async {
    final path = file.path;
    if (path == null) {
      throw const FormatException('The selected file is not available on this device.');
    }
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/api/tasks/upload'),
    )
      ..fields['task_type'] = taskType
      ..fields['cpu_cycles_giga'] = cpuCyclesGiga.toString()
      ..fields['name'] = file.name
      ..files.add(await http.MultipartFile.fromPath('file', path));
    final response = await request.send().timeout(const Duration(seconds: 60));
    return _decode(await http.Response.fromStream(response));
  }

  static dynamic _decode(http.Response response) {
    final dynamic body;
    try {
      body = jsonDecode(response.body);
    } on FormatException {
      throw HttpException(
        'The backend returned an invalid response (HTTP ${response.statusCode}).',
      );
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final detail = body is Map<String, dynamic> ? body['detail'] : null;
      throw HttpException(
        detail?.toString() ?? 'Request failed (HTTP ${response.statusCode}).',
      );
    }
    return body;
  }
}

class HttpException implements Exception {
  const HttpException(this.message);

  final String message;

  @override
  String toString() => message;
}
