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
// loadAllIndividualExtensions() // Disabled: prevents building unneeded / NSFW sources

// 1. Comprehensive Global Catalogs & Aggregators
loadIndividualExtension("all", "mangafire")
loadIndividualExtension("all", "mangadex")
loadIndividualExtension("all", "mangaupdates")
loadIndividualExtension("all", "batoto")
loadIndividualExtension("all", "comick")

// 2. High-Quality Webtoon & Manga Aggregators
loadIndividualExtension("en", "weebcentral")
loadIndividualExtension("en", "webtoons")
loadIndividualExtension("en", "webnovel")

// 3. Top Action / Fantasy Manhwa Scanlators & Portals
loadIndividualExtension("en", "comicasura")
loadIndividualExtension("en", "flamecomics")
loadIndividualExtension("en", "infernalvoidscans") // Hive Scans package
loadIndividualExtension("en", "drakescan")
loadIndividualExtension("en", "mistscans")
loadIndividualExtension("en", "thunderscans")
loadIndividualExtension("en", "elftoon")

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
fun loadAllIndividualExtensions() {
    File(rootDir, "src").eachDir { dir ->
        dir.eachDir { subdir ->
            include("src:${dir.name}:${subdir.name}")
        }
    }
}

fun loadIndividualExtension(lang: String, name: String) {
    include("src:$lang:$name")
}

fun File.eachDir(block: (File) -> Unit) {
    val files = listFiles() ?: return
    for (file in files) {
        if (file.isDirectory && file.name != ".gradle" && file.name != "build") {
            block(file)
        }
    }
}
