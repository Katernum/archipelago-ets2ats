"""
ctypes mirror of the shared-memory struct written by ETSSharedMemoryMapPlugin64v2.dll
(the "ETS2 SharedMemory" plugin -- already installed on this machine, and the same layout
RenCloud/scs-sdk-plugin maintains for compatibility with the wider dashboard/tool ecosystem).

Field names, order, and types are ported directly from the plugin's own source,
`scs-telemetry/inc/scs-telemetry-common.hpp` in github.com/RenCloud/scs-sdk-plugin
(struct `scsTelemetryMap_s`) -- not reverse engineered. That header annotates every zone
boundary with its exact byte offset in comments; several were spot-checked by hand-summing
field sizes against the documented offsets (e.g. zone 2 sums to exactly 460 bytes, landing
on the documented "END OF SECOND ZONE AT OFFSET 499" starting from offset 40) and matched,
which is why this mirror uses ctypes' default (natural/no explicit packing) struct layout
rather than `_pack_ = 1` -- the source's own placeholder/padding fields already account for
whatever the compiler's natural alignment would insert.

The `trailer` zone (10 x scsTrailer_t, offset ~6000 onward) is deliberately left as an
opaque byte blob here -- Milestone 2 only needs the truck/job/gameplay-event fields that
come before it, and getting the trailer sub-struct wrong wouldn't affect anything earlier
in the layout.

Memory-mapped file name: ``Local\\SCSTelemetry``, size 32768 bytes (only ~21.6KB is the
actual struct; the rest is reserved slack).
"""

import ctypes

MMF_NAME = "SCSTelemetry"  # opened in the caller's session namespace, equivalent to "Local\\SCSTelemetry"
MMF_SIZE = 32 * 1024

STRINGSIZE = 64


def _cstr(n: int = STRINGSIZE):
    return ctypes.c_char * n


class ScsValues(ctypes.Structure):
    _fields_ = [
        ("telemetry_plugin_revision", ctypes.c_uint32),
        ("version_major", ctypes.c_uint32),
        ("version_minor", ctypes.c_uint32),
        ("game", ctypes.c_uint32),  # 0 unknown, 1 ETS2, 2 ATS
        ("telemetry_version_game_major", ctypes.c_uint32),
        ("telemetry_version_game_minor", ctypes.c_uint32),
    ]


class CommonUi(ctypes.Structure):
    _fields_ = [("time_abs", ctypes.c_uint32)]


class ConfigUi(ctypes.Structure):
    _fields_ = [
        ("gears", ctypes.c_uint32),
        ("gears_reverse", ctypes.c_uint32),
        ("retarderStepCount", ctypes.c_uint32),
        ("truckWheelCount", ctypes.c_uint32),
        ("selectorCount", ctypes.c_uint32),
        ("time_abs_delivery", ctypes.c_uint32),
        ("maxTrailerCount", ctypes.c_uint32),
        ("unitCount", ctypes.c_uint32),
        ("plannedDistanceKm", ctypes.c_uint32),
    ]


class TruckUi(ctypes.Structure):
    _fields_ = [
        ("shifterSlot", ctypes.c_uint32),
        ("retarderBrake", ctypes.c_uint32),
        ("lightsAuxFront", ctypes.c_uint32),
        ("lightsAuxRoof", ctypes.c_uint32),
        ("truck_wheelSubstance", ctypes.c_uint32 * 16),
        ("hshifterPosition", ctypes.c_uint32 * 32),
        ("hshifterBitmask", ctypes.c_uint32 * 32),
    ]


class GameplayUi(ctypes.Structure):
    _fields_ = [
        ("jobDeliveredDeliveryTime", ctypes.c_uint32),
        ("jobStartingTime", ctypes.c_uint32),
        ("jobFinishedTime", ctypes.c_uint32),
    ]


class CommonI(ctypes.Structure):
    _fields_ = [("restStop", ctypes.c_int32)]


class TruckI(ctypes.Structure):
    _fields_ = [
        ("gear", ctypes.c_int32),
        ("gearDashboard", ctypes.c_int32),
        ("hshifterResulting", ctypes.c_int32 * 32),
    ]


class GameplayI(ctypes.Structure):
    _fields_ = [("jobDeliveredEarnedXp", ctypes.c_int32)]


class CommonF(ctypes.Structure):
    _fields_ = [("scale", ctypes.c_float)]


class ConfigF(ctypes.Structure):
    _fields_ = [
        ("fuelCapacity", ctypes.c_float),
        ("fuelWarningFactor", ctypes.c_float),
        ("adblueCapacity", ctypes.c_float),
        ("adblueWarningFactor", ctypes.c_float),
        ("airPressureWarning", ctypes.c_float),
        ("airPressurEmergency", ctypes.c_float),
        ("oilPressureWarning", ctypes.c_float),
        ("waterTemperatureWarning", ctypes.c_float),
        ("batteryVoltageWarning", ctypes.c_float),
        ("engineRpmMax", ctypes.c_float),
        ("gearDifferential", ctypes.c_float),
        ("cargoMass", ctypes.c_float),
        ("truckWheelRadius", ctypes.c_float * 16),
        ("gearRatiosForward", ctypes.c_float * 24),
        ("gearRatiosReverse", ctypes.c_float * 8),
        ("unitMass", ctypes.c_float),
    ]


class TruckF(ctypes.Structure):
    _fields_ = [
        ("speed", ctypes.c_float),
        ("engineRpm", ctypes.c_float),
        ("userSteer", ctypes.c_float),
        ("userThrottle", ctypes.c_float),
        ("userBrake", ctypes.c_float),
        ("userClutch", ctypes.c_float),
        ("gameSteer", ctypes.c_float),
        ("gameThrottle", ctypes.c_float),
        ("gameBrake", ctypes.c_float),
        ("gameClutch", ctypes.c_float),
        ("cruiseControlSpeed", ctypes.c_float),
        ("airPressure", ctypes.c_float),
        ("brakeTemperature", ctypes.c_float),
        ("fuel", ctypes.c_float),
        ("fuelAvgConsumption", ctypes.c_float),
        ("fuelRange", ctypes.c_float),
        ("adblue", ctypes.c_float),
        ("oilPressure", ctypes.c_float),
        ("oilTemperature", ctypes.c_float),
        ("waterTemperature", ctypes.c_float),
        ("batteryVoltage", ctypes.c_float),
        ("lightsDashboard", ctypes.c_float),
        ("wearEngine", ctypes.c_float),
        ("wearTransmission", ctypes.c_float),
        ("wearCabin", ctypes.c_float),
        ("wearChassis", ctypes.c_float),
        ("wearWheels", ctypes.c_float),
        ("truckOdometer", ctypes.c_float),
        ("routeDistance", ctypes.c_float),
        ("routeTime", ctypes.c_float),
        ("speedLimit", ctypes.c_float),
        ("truck_wheelSuspDeflection", ctypes.c_float * 16),
        ("truck_wheelVelocity", ctypes.c_float * 16),
        ("truck_wheelSteering", ctypes.c_float * 16),
        ("truck_wheelRotation", ctypes.c_float * 16),
        ("truck_wheelLift", ctypes.c_float * 16),
        ("truck_wheelLiftOffset", ctypes.c_float * 16),
    ]


class GameplayF(ctypes.Structure):
    _fields_ = [
        ("jobDeliveredCargoDamage", ctypes.c_float),
        ("jobDeliveredDistanceKm", ctypes.c_float),
        ("refuelAmount", ctypes.c_float),
    ]


class JobF(ctypes.Structure):
    _fields_ = [("cargoDamage", ctypes.c_float)]


class ConfigB(ctypes.Structure):
    _fields_ = [
        ("truckWheelSteerable", ctypes.c_bool * 16),
        ("truckWheelSimulated", ctypes.c_bool * 16),
        ("truckWheelPowered", ctypes.c_bool * 16),
        ("truckWheelLiftable", ctypes.c_bool * 16),
        ("isCargoLoaded", ctypes.c_bool),
        ("specialJob", ctypes.c_bool),
    ]


class TruckB(ctypes.Structure):
    _fields_ = [
        ("parkBrake", ctypes.c_bool),
        ("motorBrake", ctypes.c_bool),
        ("airPressureWarning", ctypes.c_bool),
        ("airPressureEmergency", ctypes.c_bool),
        ("fuelWarning", ctypes.c_bool),
        ("adblueWarning", ctypes.c_bool),
        ("oilPressureWarning", ctypes.c_bool),
        ("waterTemperatureWarning", ctypes.c_bool),
        ("batteryVoltageWarning", ctypes.c_bool),
        ("electricEnabled", ctypes.c_bool),
        ("engineEnabled", ctypes.c_bool),
        ("wipers", ctypes.c_bool),
        ("blinkerLeftActive", ctypes.c_bool),
        ("blinkerRightActive", ctypes.c_bool),
        ("blinkerLeftOn", ctypes.c_bool),
        ("blinkerRightOn", ctypes.c_bool),
        ("lightsParking", ctypes.c_bool),
        ("lightsBeamLow", ctypes.c_bool),
        ("lightsBeamHigh", ctypes.c_bool),
        ("lightsBeacon", ctypes.c_bool),
        ("lightsBrake", ctypes.c_bool),
        ("lightsReverse", ctypes.c_bool),
        ("lightsHazard", ctypes.c_bool),
        ("cruiseControl", ctypes.c_bool),
        ("truck_wheelOnGround", ctypes.c_bool * 16),
        ("shifterToggle", ctypes.c_bool * 2),
        ("differentialLock", ctypes.c_bool),
        ("liftAxle", ctypes.c_bool),
        ("liftAxleIndicator", ctypes.c_bool),
        ("trailerLiftAxle", ctypes.c_bool),
        ("trailerLiftAxleIndicator", ctypes.c_bool),
    ]


class GameplayB(ctypes.Structure):
    _fields_ = [
        ("jobDeliveredAutoparkUsed", ctypes.c_bool),
        ("jobDeliveredAutoloadUsed", ctypes.c_bool),
    ]


class ConfigFv(ctypes.Structure):
    _fields_ = [
        ("cabinPositionX", ctypes.c_float),
        ("cabinPositionY", ctypes.c_float),
        ("cabinPositionZ", ctypes.c_float),
        ("headPositionX", ctypes.c_float),
        ("headPositionY", ctypes.c_float),
        ("headPositionZ", ctypes.c_float),
        ("truckHookPositionX", ctypes.c_float),
        ("truckHookPositionY", ctypes.c_float),
        ("truckHookPositionZ", ctypes.c_float),
        ("truckWheelPositionX", ctypes.c_float * 16),
        ("truckWheelPositionY", ctypes.c_float * 16),
        ("truckWheelPositionZ", ctypes.c_float * 16),
    ]


class TruckFv(ctypes.Structure):
    _fields_ = [
        ("lv_accelerationX", ctypes.c_float),
        ("lv_accelerationY", ctypes.c_float),
        ("lv_accelerationZ", ctypes.c_float),
        ("av_accelerationX", ctypes.c_float),
        ("av_accelerationY", ctypes.c_float),
        ("av_accelerationZ", ctypes.c_float),
        ("accelerationX", ctypes.c_float),
        ("accelerationY", ctypes.c_float),
        ("accelerationZ", ctypes.c_float),
        ("aa_accelerationX", ctypes.c_float),
        ("aa_accelerationY", ctypes.c_float),
        ("aa_accelerationZ", ctypes.c_float),
        ("cabinAVX", ctypes.c_float),
        ("cabinAVY", ctypes.c_float),
        ("cabinAVZ", ctypes.c_float),
        ("cabinAAX", ctypes.c_float),
        ("cabinAAY", ctypes.c_float),
        ("cabinAAZ", ctypes.c_float),
    ]


class TruckFp(ctypes.Structure):
    _fields_ = [
        ("cabinOffsetX", ctypes.c_float),
        ("cabinOffsetY", ctypes.c_float),
        ("cabinOffsetZ", ctypes.c_float),
        ("cabinOffsetrotationX", ctypes.c_float),
        ("cabinOffsetrotationY", ctypes.c_float),
        ("cabinOffsetrotationZ", ctypes.c_float),
        ("headOffsetX", ctypes.c_float),
        ("headOffsetY", ctypes.c_float),
        ("headOffsetZ", ctypes.c_float),
        ("headOffsetrotationX", ctypes.c_float),
        ("headOffsetrotationY", ctypes.c_float),
        ("headOffsetrotationZ", ctypes.c_float),
    ]


class TruckDp(ctypes.Structure):
    _fields_ = [
        ("coordinateX", ctypes.c_double),
        ("coordinateY", ctypes.c_double),
        ("coordinateZ", ctypes.c_double),
        ("rotationX", ctypes.c_double),
        ("rotationY", ctypes.c_double),
        ("rotationZ", ctypes.c_double),
    ]


class ConfigS(ctypes.Structure):
    _fields_ = [
        ("truckBrandId", _cstr()),
        ("truckBrand", _cstr()),
        ("truckId", _cstr()),
        ("truckName", _cstr()),
        ("cargoId", _cstr()),
        ("cargo", _cstr()),
        ("cityDstId", _cstr()),
        ("cityDst", _cstr()),
        ("compDstId", _cstr()),
        ("compDst", _cstr()),
        ("citySrcId", _cstr()),
        ("citySrc", _cstr()),
        ("compSrcId", _cstr()),
        ("compSrc", _cstr()),
        ("shifterType", _cstr(16)),
        ("truckLicensePlate", _cstr()),
        ("truckLicensePlateCountryId", _cstr()),
        ("truckLicensePlateCountry", _cstr()),
        ("jobMarket", _cstr(32)),
    ]


class GameplayS(ctypes.Structure):
    _fields_ = [
        ("fineOffence", _cstr(32)),
        ("ferrySourceName", _cstr()),
        ("ferryTargetName", _cstr()),
        ("ferrySourceId", _cstr()),
        ("ferryTargetId", _cstr()),
        ("trainSourceName", _cstr()),
        ("trainTargetName", _cstr()),
        ("trainSourceId", _cstr()),
        ("trainTargetId", _cstr()),
    ]


class ConfigUll(ctypes.Structure):
    _fields_ = [("jobIncome", ctypes.c_uint64)]


class GameplayLl(ctypes.Structure):
    _fields_ = [
        ("jobCancelledPenalty", ctypes.c_int64),
        ("jobDeliveredRevenue", ctypes.c_int64),
        ("fineAmount", ctypes.c_int64),
        ("tollgatePayAmount", ctypes.c_int64),
        ("ferryPayAmount", ctypes.c_int64),
        ("trainPayAmount", ctypes.c_int64),
    ]


class SpecialB(ctypes.Structure):
    _fields_ = [
        ("onJob", ctypes.c_bool),
        ("jobFinished", ctypes.c_bool),
        ("jobCancelled", ctypes.c_bool),
        ("jobDelivered", ctypes.c_bool),
        ("fined", ctypes.c_bool),
        ("tollgate", ctypes.c_bool),
        ("ferry", ctypes.c_bool),
        ("train", ctypes.c_bool),
        ("refuel", ctypes.c_bool),
        ("refuelPayed", ctypes.c_bool),
    ]


class Substances(ctypes.Structure):
    _fields_ = [("substance", (ctypes.c_char * STRINGSIZE) * 25)]


class ScsTelemetryMap(ctypes.Structure):
    _fields_ = [
        ("sdkActive", ctypes.c_bool),
        ("placeHolder", ctypes.c_char * 3),
        ("paused", ctypes.c_bool),
        ("placeHolder2", ctypes.c_char * 3),
        ("time", ctypes.c_uint64),
        ("simulatedTime", ctypes.c_uint64),
        ("renderTime", ctypes.c_uint64),
        ("multiplayerTimeOffset", ctypes.c_int64),

        ("scs_values", ScsValues),
        ("common_ui", CommonUi),
        ("config_ui", ConfigUi),
        ("truck_ui", TruckUi),
        ("gameplay_ui", GameplayUi),
        ("buffer_ui", ctypes.c_char * 48),

        ("common_i", CommonI),
        ("truck_i", TruckI),
        ("gameplay_i", GameplayI),
        ("buffer_i", ctypes.c_char * 56),

        ("common_f", CommonF),
        ("config_f", ConfigF),
        ("truck_f", TruckF),
        ("gameplay_f", GameplayF),
        ("job_f", JobF),
        ("buffer_f", ctypes.c_char * 28),

        ("config_b", ConfigB),
        ("truck_b", TruckB),
        ("gameplay_b", GameplayB),
        ("buffer_b", ctypes.c_char * 25),

        ("config_fv", ConfigFv),
        ("truck_fv", TruckFv),
        ("buffer_fv", ctypes.c_char * 60),

        ("truck_fp", TruckFp),
        ("buffer_fp", ctypes.c_char * 152),

        ("truck_dp", TruckDp),
        ("buffer_dp", ctypes.c_char * 52),

        ("config_s", ConfigS),
        ("gameplay_s", GameplayS),
        ("buffer_s", ctypes.c_char * 20),

        ("config_ull", ConfigUll),
        ("buffer_ull", ctypes.c_char * 192),

        ("gameplay_ll", GameplayLl),
        ("buffer_ll", ctypes.c_char * 52),

        ("special_b", SpecialB),
        ("buffer_special", ctypes.c_char * 90),

        ("substances", Substances),

        # Opaque: 10x scsTrailer_t, not modeled -- not needed before this offset.
        ("trailer_zone", ctypes.c_ubyte * (1560 * 10)),
    ]
