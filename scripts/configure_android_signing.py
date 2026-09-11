from pathlib import Path

app_kts = Path('.build_app/android/app/build.gradle.kts')
app_groovy = Path('.build_app/android/app/build.gradle')

if app_kts.exists():
    s = app_kts.read_text(encoding='utf-8')
    if 'val keystoreProperties = Properties()' not in s:
        s = 'import java.util.Properties\nimport java.io.FileInputStream\n\n' + s
        prelude = '''val keystoreProperties = Properties()\nval keystorePropertiesFile = rootProject.file("key.properties")\nkeystoreProperties.load(FileInputStream(keystorePropertiesFile))\n\n'''
        s = s.replace('android {', prelude + 'android {', 1)
        block = '''    signingConfigs {\n        create("release") {\n            keyAlias = keystoreProperties["keyAlias"] as String\n            keyPassword = keystoreProperties["keyPassword"] as String\n            storeFile = keystoreProperties["storeFile"]?.let { file(it) }\n            storePassword = keystoreProperties["storePassword"] as String\n        }\n    }\n\n'''
        s = s.replace('    buildTypes {', block + '    buildTypes {', 1)
    s = s.replace('signingConfig = signingConfigs.getByName("debug")', 'signingConfig = signingConfigs.getByName("release")')
    app_kts.write_text(s, encoding='utf-8')
elif app_groovy.exists():
    s = app_groovy.read_text(encoding='utf-8')
    if 'def keystoreProperties = new Properties()' not in s:
        prelude = '''def keystoreProperties = new Properties()\ndef keystorePropertiesFile = rootProject.file('key.properties')\nkeystoreProperties.load(new FileInputStream(keystorePropertiesFile))\n\n'''
        s = s.replace('android {', prelude + 'android {', 1)
        block = '''    signingConfigs {\n        release {\n            keyAlias keystoreProperties['keyAlias']\n            keyPassword keystoreProperties['keyPassword']\n            storeFile file(keystoreProperties['storeFile'])\n            storePassword keystoreProperties['storePassword']\n        }\n    }\n\n'''
        s = s.replace('    buildTypes {', block + '    buildTypes {', 1)
    s = s.replace('signingConfig signingConfigs.debug', 'signingConfig signingConfigs.release')
    app_groovy.write_text(s, encoding='utf-8')
else:
    raise SystemExit('Fichier Gradle Android introuvable')
