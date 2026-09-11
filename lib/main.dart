import 'dart:io';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';

const String kHomeUrl = 'https://www.clairvoyancemedium.com/';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ClairVoyanceMediumApp());
}

class ClairVoyanceMediumApp extends StatelessWidget {
  const ClairVoyanceMediumApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'ClairVoyanceMedium.com',
      theme: ThemeData(
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFD7AD4A),
          brightness: Brightness.dark,
        ),
        scaffoldBackgroundColor: Colors.black,
      ),
      home: const WebsiteShell(),
    );
  }
}

class WebsiteShell extends StatefulWidget {
  const WebsiteShell({super.key});

  @override
  State<WebsiteShell> createState() => _WebsiteShellState();
}

class _WebsiteShellState extends State<WebsiteShell> {
  late final WebViewController _controller;
  final WebViewCookieManager _cookieManager = WebViewCookieManager();

  int _progress = 0;
  bool _mainFrameError = false;
  String? _errorText;

  @override
  void initState() {
    super.initState();
    _initWebView();
  }

  Future<void> _initWebView() async {
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.black)
      ..setNavigationDelegate(
        NavigationDelegate(
          onProgress: (progress) {
            if (!mounted) return;
            setState(() => _progress = progress);
          },
          onPageStarted: (_) {
            if (!mounted) return;
            setState(() {
              _mainFrameError = false;
              _errorText = null;
            });
          },
          onPageFinished: (_) {
            if (!mounted) return;
            setState(() => _progress = 100);
          },
          onWebResourceError: (error) {
            if (error.isForMainFrame == true && mounted) {
              setState(() {
                _mainFrameError = true;
                _errorText = error.description;
              });
            }
          },
          onNavigationRequest: (request) {
            final uri = Uri.tryParse(request.url);
            if (uri == null) return NavigationDecision.navigate;

            if (uri.scheme == 'http' || uri.scheme == 'https') {
              // Les paiements, 3-D Secure, PayPal, Stripe et tawk.to restent
              // dans la même WebView afin de préserver la session et le panier.
              return NavigationDecision.navigate;
            }

            _openExternal(uri);
            return NavigationDecision.prevent;
          },
        ),
      );

    if (Platform.isAndroid &&
        _controller.platform is AndroidWebViewController &&
        _cookieManager.platform is AndroidWebViewCookieManager) {
      final androidController =
          _controller.platform as AndroidWebViewController;
      final androidCookies =
          _cookieManager.platform as AndroidWebViewCookieManager;

      // Important pour les parcours de paiement, widgets tiers et sessions.
      await androidCookies.setAcceptThirdPartyCookies(androidController, true);
      await androidController.setMediaPlaybackRequiresUserGesture(false);
      await androidController.setPaymentRequestEnabled(true);
      await androidController.setUseWideViewPort(true);
    }

    await _controller.loadRequest(Uri.parse(kHomeUrl));
  }

  Future<void> _openExternal(Uri uri) async {
    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      // Si aucune application ne sait gérer le protocole, on ne bloque pas
      // l'application principale.
    }
  }

  Future<bool> _handleBack() async {
    if (await _controller.canGoBack()) {
      await _controller.goBack();
      return false;
    }
    return true;
  }

  Future<void> _reloadHome() async {
    if (!mounted) return;
    setState(() {
      _mainFrameError = false;
      _errorText = null;
      _progress = 0;
    });
    await _controller.loadRequest(Uri.parse(kHomeUrl));
  }

  @override
  Widget build(BuildContext context) {
    return WillPopScope(
      onWillPop: _handleBack,
      child: Scaffold(
        body: SafeArea(
          child: Stack(
            children: [
              if (!_mainFrameError)
                WebViewWidget(controller: _controller)
              else
                _OfflineView(
                  message: _errorText,
                  onRetry: _reloadHome,
                ),
              if (_progress < 100 && !_mainFrameError)
                Align(
                  alignment: Alignment.topCenter,
                  child: LinearProgressIndicator(
                    value: _progress / 100,
                    minHeight: 2,
                    backgroundColor: Colors.transparent,
                    color: const Color(0xFFD7AD4A),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _OfflineView extends StatelessWidget {
  const _OfflineView({required this.onRetry, this.message});

  final Future<void> Function() onRetry;
  final String? message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.wifi_off_rounded,
                  size: 54, color: Color(0xFFD7AD4A)),
              const SizedBox(height: 18),
              const Text(
                'Connexion indisponible',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 10),
              Text(
                message?.isNotEmpty == true
                    ? message!
                    : 'Vérifiez votre connexion Internet puis réessayez.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white70),
              ),
              const SizedBox(height: 22),
              FilledButton(
                onPressed: onRetry,
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFFD7AD4A),
                  foregroundColor: Colors.black,
                ),
                child: const Text('Réessayer'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
