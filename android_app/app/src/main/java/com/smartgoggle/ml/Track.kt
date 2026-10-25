package com.smartgoggle.ml

data class Track(
    val trackId: Int,
    val className: String,
    val bbox: FloatArray,
    val distance: Float = 0f,
    val position: String = "unknown",
    val movement: String = "stationary",
    val dangerLevel: String = "low"
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false

        other as Track

        if (trackId != other.trackId) return false
        if (className != other.className) return false
        if (!bbox.contentEquals(other.bbox)) return false
        if (distance != other.distance) return false
        if (position != other.position) return false
        if (movement != other.movement) return false
        if (dangerLevel != other.dangerLevel) return false

        return true
    }

    override fun hashCode(): Int {
        var result = trackId
        result = 31 * result + className.hashCode()
        result = 31 * result + bbox.contentHashCode()
        result = 31 * result + distance.hashCode()
        result = 31 * result + position.hashCode()
        result = 31 * result + movement.hashCode()
        result = 31 * result + dangerLevel.hashCode()
        return result
    }
}

