import 'dart:io';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:onesignal_flutter/onesignal_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';

const String kHomeUrl = 'https://www.clairvoyancemedium.com/';
const String kOneSignalAppId = '1252e604-9e9d-4d50-9e4e-ca1ae6b624e3';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  _initPushInfrastructure();
  runApp(const ClairVoyanceMediumPlayStoreApp());
}

void _initPushInfrastructure() {
  OneSignal.initialize(kOneSignalAppId);

  final platform = Platform.isAndroid
      ? 'android_native'
      : Platform.isIOS
          ? 'ios_native'
          : 'other';

  OneSignal.User.addTags({
    'brand': 'clairvoyancemedium',
    'platform': platform,
    'distribution': Platform.isAndroid ? 'play_store' : 'native',
  });

  OneSignal.User.trackEvent('app_open');
  _registerFirstInstallTelemetry(platform);
}

Future<void> _registerFirstInstallTelemetry(String platform) async {
  try {
    final prefs = await SharedPreferences.getInstance();

    var installId = prefs.getString('cvm_install_id');
    if (installId == null || installId.isEmpty) {
      final random = Random.secure();
      installId = [
        DateTime.now().microsecondsSinceEpoch.toRadixString(36),
        random.nextInt(1 << 30).toRadixString(36),
        random.nextInt(1 << 30).toRadixString(36),
      ].join();
      await prefs.setString('cvm_install_id', installId);
    }

    var firstInstallTs = prefs.getInt('cvm_first_install_ts');
    if (firstInstallTs == null || firstInstallTs <= 0) {
      firstInstallTs = DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000;
      await prefs.setInt('cvm_first_install_ts', firstInstallTs);
    }

    OneSignal.User.addTags({
      'install_id': installId,
      'first_install_ts': firstInstallTs.toString(),
      'install_source': Platform.isAndroid
          ? 'play_store'
          : Platform.isIOS
              ? 'native_ios'
              : 'native',
      'device_locale': Platform.localeName,
      'tz_offset_min': DateTime.now().timeZoneOffset.inMinutes.toString(),
      'platform': platform,
    });

    final eventAlreadySent =
        prefs.getBool('cvm_first_install_event_sent') ?? false;
    if (!eventAlreadySent) {
      OneSignal.User.trackEvent('first_install');
      await prefs.setBool('cvm_first_install_event_sent', true);
    }
  } catch (_) {
    // La télémétrie ne doit jamais empêcher l'application de démarrer.
  }
}

class ClairVoyanceMediumPlayStoreApp extends StatelessWidget {
  const ClairVoyanceMediumPlayStoreApp({super.key});

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
      home: const PlayStoreLaunchGate(),
    );
  }
}

class PlayStoreLaunchGate extends StatefulWidget {
  const PlayStoreLaunchGate({super.key});

  @override
  State<PlayStoreLaunchGate> createState() => _PlayStoreLaunchGateState();
}

class _PlayStoreLaunchGateState extends State<PlayStoreLaunchGate> {
  bool _showWebsite = false;

  @override
  void initState() {
    super.initState();
    Future<void>.delayed(const Duration(milliseconds: 1150), () {
      if (mounted) setState(() => _showWebsite = true);
    });
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 260),
      child: _showWebsite
          ? const WebsiteShell(key: ValueKey('website'))
          : const _OfficialSplash(key: ValueKey('splash')),
    );
  }
}

class _OfficialSplash extends StatelessWidget {
  const _OfficialSplash({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final logoSize = (constraints.maxWidth * 0.34).clamp(112.0, 164.0);
            return Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 28),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 430),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Image.asset(
                        'assets/app_icon.jpg',
                        width: logoSize,
                        height: logoSize,
                        fit: BoxFit.contain,
                      ),
                      const SizedBox(height: 24),
                      const FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text(
                          'ClairVoyanceMedium.com',
                          maxLines: 1,
                          style: TextStyle(
                            color: Color(0xFFD7AD4A),
                            fontSize: 30,
                            fontWeight: FontWeight.w600,
                            letterSpacing: .15,
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Since 1998',
                        style: TextStyle(
                          color: Colors.white70,
                          fontSize: 16,
                          letterSpacing: 1.4,
                        ),
                      ),
                      const SizedBox(height: 38),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(99),
                        child: const SizedBox(
                          width: 180,
                          child: LinearProgressIndicator(
                            minHeight: 4,
                            backgroundColor: Color(0xFF242424),
                            color: Color(0xFFD7AD4A),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
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
              // Les pages du site, Stripe, 3-D Secure, PayPal et tawk.to restent
              // dans la WebView afin de conserver la session utilisateur.
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
    if (_pushPromptScheduled || !mounted) return;
    _pushPromptScheduled = true;
    Future<void>.delayed(
      const Duration(milliseconds: 900),
      _maybePromptNotifications,
    );
  }

  Future<void> _ensurePushSubscribed() async {
    if (!(Platform.isAndroid || Platform.isIOS)) return;
    if (!OneSignal.Notifications.permission) return;

    try {
      await OneSignal.User.pushSubscription.optIn();
      OneSignal.User.addTags({
        'push_permission': 'granted',
        'push_opted_in': 'true',
      });
      OneSignal.User.trackEvent('push_subscription_refreshed');
    } catch (_) {
      // Une indisponibilité temporaire de OneSignal ne doit pas bloquer l'app.
    }
  }

  Future<void> _maybePromptNotifications() async {
    if (!mounted) return;

    final prefs = await SharedPreferences.getInstance();
    final alreadyExplained = prefs.getBool('push_explainer_seen') ?? false;
    final permissionGranted = OneSignal.Notifications.permission;

    if (permissionGranted) {
      await _ensurePushSubscribed();
      return;
    }

    if (alreadyExplained || !mounted) return;

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
      final permissionNowGranted = OneSignal.Notifications.permission;

      if (permissionNowGranted) {
        await _ensurePushSubscribed();
      }

      OneSignal.User.trackEvent('push_permission_prompted');
      OneSignal.User.addTags({
        'push_permission': permissionNowGranted ? 'granted' : 'not_granted',
        'push_opted_in': permissionNowGranted ? 'true' : 'false',
      });
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
