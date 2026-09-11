import 'dart:io';

import 'package:flutter/material.dart';
import 'package:onesignal_flutter/onesignal_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';

const String kHomeUrl = 'https://www.clairvoyancemedium.com/';
const String kOneSignalAppId = String.fromEnvironment(
  'ONESIGNAL_APP_ID',
  defaultValue: '',
);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  _initPushInfrastructure();
  runApp(const ClairVoyanceMediumApp());
}

void _initPushInfrastructure() {
  if (kOneSignalAppId.isEmpty) return;

  OneSignal.initialize(kOneSignalAppId);

  final platform = Platform.isAndroid
      ? 'android_native'
      : Platform.isIOS
          ? 'ios_native'
          : 'other';

  OneSignal.User.addTags({
    'brand': 'clairvoyancemedium',
    'platform': platform,
    'distribution': Platform.isAndroid ? 'direct_apk' : 'native',
  });

  // OneSignal suit automatiquement les sessions, la version de l'appareil,
  // le système, la version de l'application et l'état de l'abonnement.
  // Cet événement facilite aussi les analyses d'ouverture côté tableau de bord.
  OneSignal.User.trackEvent('app_open');
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
  bool _pushPromptScheduled = false;
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
            _schedulePushPrompt();
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
              // Stripe, 3-D Secure, PayPal et tawk.to restent dans la WebView
              // afin de préserver le panier et la session utilisateur.
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
      final androidController = _controller.platform as AndroidWebViewController;
      final androidCookies =
          _cookieManager.platform as AndroidWebViewCookieManager;

      await androidCookies.setAcceptThirdPartyCookies(androidController, true);
      await androidController.setMediaPlaybackRequiresUserGesture(false);
      await androidController.setPaymentRequestEnabled(true);
      await androidController.setUseWideViewPort(true);
    }

    await _controller.loadRequest(Uri.parse(kHomeUrl));
  }

  void _schedulePushPrompt() {
    if (_pushPromptScheduled || kOneSignalAppId.isEmpty || !mounted) return;
    _pushPromptScheduled = true;
    Future<void>.delayed(const Duration(milliseconds: 900), _maybePromptNotifications);
  }

  Future<void> _maybePromptNotifications() async {
    if (!mounted || kOneSignalAppId.isEmpty) return;

    final prefs = await SharedPreferences.getInstance();
    final alreadyExplained = prefs.getBool('push_explainer_seen') ?? false;
    final permissionGranted = OneSignal.Notifications.permission;

    if (permissionGranted || alreadyExplained || !mounted) return;

    final accepted = await showDialog<bool>(
      context: context,
      barrierDismissible: true,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF111111),
        title: const Text('Recevoir nos notifications'),
        content: const Text(
          'Autorisez les notifications pour recevoir les nouveautés, offres et informations importantes de ClairVoyanceMedium.com. Vous pourrez les désactiver à tout moment dans les réglages du téléphone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Plus tard'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFFD7AD4A),
              foregroundColor: Colors.black,
            ),
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Autoriser'),
          ),
        ],
      ),
    );

    await prefs.setBool('push_explainer_seen', true);

    if (accepted == true) {
      await OneSignal.Notifications.requestPermission(true);
      OneSignal.User.trackEvent('push_permission_prompted');
      OneSignal.User.addTag(
        'push_permission',
        OneSignal.Notifications.permission ? 'granted' : 'not_granted',
      );
    }
  }

  Future<void> _openExternal(Uri uri) async {
    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      // Aucun blocage si le protocole n'est pas géré par l'appareil.
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
              const Icon(
                Icons.wifi_off_rounded,
                size: 54,
                color: Color(0xFFD7AD4A),
              ),
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
