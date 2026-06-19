plugins {
    id("com.android.application") version "8.13.0" apply false
    id("org.jetbrains.kotlin.android") version "2.1.20" apply false
}

tasks.wrapper {
    gradleVersion = "8.13"
    distributionType = Wrapper.DistributionType.BIN
    distributionSha256Sum =
        "20f1b1176237254a6fc204d8434196fa11a4cfb387567519c61556e8710aed78"
}
