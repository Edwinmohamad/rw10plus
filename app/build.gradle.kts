import java.util.Properties

plugins { id("com.android.application") }

val serverUrl = providers.gradleProperty("RW10_SERVER_URL").orElse("http://192.168.100.50:8188/")
val signingFile = rootProject.file("keystore.properties")
val signingProps = Properties().apply { if (signingFile.exists()) signingFile.inputStream().use(::load) }

android {
    namespace = "id.rw10.app"
    compileSdk = 36

    defaultConfig {
        applicationId = "id.rw10.app"
        minSdk = 26
        targetSdk = 36
        versionCode = 4
        versionName = "0.3.0-internal"
        buildConfigField("String", "SERVER_URL", "\"${serverUrl.get()}\"")
    }

    signingConfigs {
        if (signingFile.exists()) {
            create("release") {
                storeFile = rootProject.file(signingProps.getProperty("storeFile"))
                storePassword = signingProps.getProperty("storePassword")
                keyAlias = signingProps.getProperty("keyAlias")
                keyPassword = signingProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            if (signingFile.exists()) signingConfig = signingConfigs.getByName("release")
        }
    }
    buildFeatures { buildConfig = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    lint { abortOnError = true; checkReleaseBuilds = true }
}


dependencies {
    implementation("androidx.activity:activity:1.10.1")
}
