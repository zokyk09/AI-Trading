import 'dart:async';
import 'dart:convert';
import 'dart:io';

class TradingApi {
  TradingApi({HttpClient? client})
    : _client =
          client ??
          (HttpClient()..connectionTimeout = const Duration(seconds: 8));

  final HttpClient _client;
  String baseUrl = '';

  Future<Map<String, dynamic>> get(String path) => _request(path);

  Future<Map<String, dynamic>> post(
    String path, {
    required Map<String, dynamic> body,
  }) => _request(path, body: body);

  Future<Map<String, dynamic>> _request(
    String path, {
    Map<String, dynamic>? body,
  }) async {
    if (baseUrl.trim().isEmpty) {
      throw const ApiException(
        'Isi alamat home server pada menu Koneksi dulu.',
      );
    }
    final root = baseUrl.trim().replaceAll(RegExp(r'/+$'), '');
    final uri = Uri.parse('$root$path');
    final request = body == null
        ? await _client.getUrl(uri)
        : await _client.postUrl(uri);
    request.headers.set(HttpHeaders.acceptHeader, 'application/json');
    if (body != null) {
      request.headers.contentType = ContentType.json;
      request.write(jsonEncode(body));
    }
    final response = await request.close();
    final text = await response.transform(utf8.decoder).join();
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException('HTTP ${response.statusCode}: $text');
    }
    final decoded = jsonDecode(text);
    if (decoded is! Map<String, dynamic>) {
      throw const ApiException(
        'Backend mengirim format data yang tidak dikenal.',
      );
    }
    return decoded;
  }

  void close() => _client.close(force: true);
}

class ApiException implements Exception {
  const ApiException(this.message);
  final String message;
  @override
  String toString() => message;
}
