@file:Suppress("ktlint:standard:kdoc")

pluginManagement {
    includeBuild("gradle/build-logic")
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
        maven(url = "https://www.jitpack.io")
    }
}

dependencyResolutionManagement {
    versionCatalogs {
        create("kei") {
            from(files("gradle/kei.versions.toml"))
        }
    }
    @Suppress("UnstableApiUsage")
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    @Suppress("UnstableApiUsage")
    repositories {
        google()
        mavenCentral()
        maven(url = "https://www.jitpack.io")
    }
}

rootProject.name = "Keiyoushi"

/**
 * =================================================================================================
 * CURATED SAFE SOURCES (NON-NSFW, MAINSTREAM MANGA & MANHWA)
 * =================================================================================================
 */
// Multi-Language Aggregators & Platforms
loadSafeExtension("all", "mangafire")
loadSafeExtension("all", "mangadex")
loadSafeExtension("all", "comicklive")
loadSafeExtension("all", "webtoons")

// English Aggregators & Scanlations
loadSafeExtension("en", "bbato")
loadSafeExtension("en", "weebcentral")
loadSafeExtension("en", "webnovel")
loadSafeExtension("en", "comicasura")
loadSafeExtension("en", "asurascans")
loadSafeExtension("en", "flamecomics")
loadSafeExtension("en", "infernalvoidscans") // Hive Scans
loadSafeExtension("en", "drakescans")
loadSafeExtension("en", "mistscans")
loadSafeExtension("en", "thunderscans")
loadSafeExtension("en", "elftoon")

/**
 * ===================================== COMMON CONFIGURATION ======================================
 */
include(":core")
include(":compiler")

// Load all modules under /lib
File(rootDir, "lib").eachDir { include("lib:${it.name}") }

// Load all modules under /lib-multisrc
File(rootDir, "lib-multisrc").eachDir { include("lib-multisrc:${it.name}") }

/**
 * ======================================== HELPER FUNCTIONS =======================================
 */
// Checks if directory exists before including to prevent Gradle configuration crashes
fun loadSafeExtension(lang: String, name: String) {
    val dir = File(rootDir, "src/$lang/$name")
    if (dir.exists() && dir.isDirectory) {
        include("src:$lang:$name")
    }
}

fun File.eachDir(block: (File) -> Unit) {
    val files = listFiles() ?: return
    for (file in files) {
        if (file.isDirectory && file.name != ".gradle" && file.name != "build") {
            block(file)
        }
    }
}
