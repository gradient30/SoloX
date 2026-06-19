plugins {
    id("com.android.application")
}

android {
    namespace = "io.solox.networkagent"
    compileSdk = 36
    buildToolsVersion = "36.0.0"
    ndkVersion = "29.0.14206865"

    defaultConfig {
        applicationId = "io.solox.networkagent"
        minSdk = 21
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        debug {
            ndk {
                abiFilters += listOf("arm64-v8a", "x86_64")
            }
        }
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
            ndk {
                abiFilters += listOf("arm64-v8a")
            }
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    lint {
        checkReleaseBuilds = false
    }

}

dependencies {
}

