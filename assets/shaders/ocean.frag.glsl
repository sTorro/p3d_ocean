/*
 * ocean.frag.glsl
 *
 * Author: storro
 * Date: 2026/02/11
 * Description: Fragment shader for rendering the ocean surface
 */

#version 430

#define PI 3.14159265358979323846

uniform sampler2D u_normal_map;
uniform sampler2D u_scene_color;
uniform sampler2D u_scene_depth;
uniform sampler2D u_detail_normal;

// --- Detail normal overlay ---
uniform float u_detail_strength;    // 0..1 blend strength
uniform float u_detail_scale;       // world-space tiling (tiles per meter)
uniform float u_detail_fade_near;   // start fading at this distance
uniform float u_detail_fade_far;    // fully faded at this distance

uniform vec3 u_camera_pos;
uniform vec3 u_light_dir;   // direction the light travels (sun rays)
uniform vec3 u_sun_color;
uniform vec3 u_sky_color;
uniform vec3 u_water_color;
uniform float u_exposure;

// Refraction
uniform float u_refraction_strength;
uniform float u_near;
uniform float u_far;

// --- Specular ---
uniform float u_roughness;          // 0..1 (lower = sharper specular)
uniform float u_specular_strength;  // multiplier

// --- Sub-surface scattering ---
uniform float u_sss_intensity;      // 0..3
uniform vec3  u_sss_color;          // e.g. turquoise glow

// --- Depth-based absorption ---
uniform vec3  u_shallow_color;      // colour in shallow / crest areas
uniform float u_absorption_depth;   // scale factor for height→depth mapping

in vec3 v_world_pos;
in vec2 v_uv;
in float v_height;
in vec4 v_clip_pos;

out vec4 frag_color;

vec3 tonemap_hdr(vec3 color, float exposure)
{
    return vec3(1.0) - exp(-color * exposure);
}

float linearize_depth(float depth, float near_plane, float far_plane)
{
    float z = depth * 2.0 - 1.0;
    return (2.0 * near_plane * far_plane) / (far_plane + near_plane - z * (far_plane - near_plane));
}

void main()
{
    vec3 n = texture(u_normal_map, v_uv).xyz;
    n = normalize(n);

    // Defensive: NaN/Inf normals (from degenerate cross products in the slope compute shader)
    // poison every lighting term and appear as black speckles.
    // if (any(isnan(n)) || any(isinf(n))) {
    //     n = vec3(0.0, 0.0, 1.0);
    // }

    vec3 view_dir = normalize(u_camera_pos - v_world_pos);
    float cam_dist = length(u_camera_pos - v_world_pos);

    // ---- Detail normal overlay ----
    // Adds high-frequency capillary wave detail that the FFT resolution can't capture
    // Sampled in world-space so it tiles independently of the FFT UV
    vec2 detail_uv = v_world_pos.xy * u_detail_scale;
    vec3 n_detail = texture(u_detail_normal, detail_uv).xyz * 2.0 - 1.0;

    // Fade detail with distance (no benefit rendering micro-ripples at 100m)
    float detail_fade = 1.0 - smoothstep(u_detail_fade_near, u_detail_fade_far, cam_dist);

    // Blend detail into base normal (perturb XY, recompute Z)
    n.xy += n_detail.xy * u_detail_strength * detail_fade;
    n = normalize(n);

    // Distance-based normal flatten
    // Only kicks in at very long range to reduce aliasing/shimmering at the horizon;
    // stays at zero for the current mesh size so waves remain visible
    float flat_t = clamp((cam_dist - 500.0) / 3000.0, 0.0, 0.5);
    n = normalize(mix(n, vec3(0.0, 0.0, 1.0), flat_t));

    float ndv = clamp(dot(n, view_dir), 0.0, 1.0);
    float fresnel = 0.04 + 0.96 * pow(1.0 - ndv, 4.0);
    vec3 light_vec = normalize(-u_light_dir);
    float diffuse = clamp(dot(n, light_vec), 0.0, 1.0);

    // ---- 1. GGX Specular highlight ----
    vec3 half_vec = normalize(light_vec + view_dir);
    float ndh = clamp(dot(n, half_vec), 0.0, 1.0);
    float r = clamp(u_roughness, 0.02, 1.0);
    float a = r * r;
    float a2 = a * a;
    float denom = ndh * ndh * (a2 - 1.0) + 1.0;
    float D = a2 / (PI * denom * denom);
    float spec = D * u_specular_strength * fresnel;
    vec3 specular = spec * u_sun_color;

    // ---- 2. Depth-based absorption ----
    // Wave crests are shallow (lighter/more transparent), troughs are deep (darker).
    // Exaggerate the effect for visual interest.
    float depth_t = clamp(-v_height * u_absorption_depth * 2.0 + 0.5, 0.0, 1.0);
    vec3 body_color = mix(u_shallow_color, u_water_color, depth_t);

    // ---- 3. Sub-surface scattering approximation ----
    // Backlit wave crests glow with transmitted light.
    float sss_mask = clamp(v_height * 0.8 + 0.2, 0.0, 1.0); // stronger on crests
    float sss_dot  = pow(clamp(dot(view_dir, -light_vec), 0.0, 1.0), 3.0);
    vec3  sss = u_sss_color * sss_mask * sss_dot * u_sss_intensity;

    // ---- Refraction with scene color + depth ----
    vec2 screen_uv = (v_clip_pos.xy / v_clip_pos.w) * 0.5 + 0.5;
    vec2 refract_uv = screen_uv + (n.xz * u_refraction_strength);
    refract_uv = clamp(refract_uv, vec2(0.001), vec2(0.999));

    vec3 scene_color = texture(u_scene_color, refract_uv).rgb;
    float scene_depth = texture(u_scene_depth, refract_uv).r;

    float surface_depth = linearize_depth(gl_FragCoord.z, u_near, u_far);
    float behind_depth = linearize_depth(scene_depth, u_near, u_far);
    float thickness = max(behind_depth - surface_depth, 0.0);

    // Transmittance: how much of the scene behind shows through.
    // When there's no scene (depth = far), thickness is huge → transmittance ≈ 0.
    float transmittance = exp(-thickness * u_absorption_depth);

    // Body lighting: ambient + diffuse contribution. Less harsh than before.
    vec3 ambient = body_color * 0.3;
    vec3 body_lit = body_color * (ambient + u_sky_color * diffuse * 0.5);

    // Refracted view: blend scene (if visible) with tinted water body.
    // When nothing is behind (transmittance ≈ 0), we see body_lit.
    vec3 refracted = mix(body_lit, scene_color, transmittance);

    // ---- 4. Procedural sky reflection ----
    // Instead of flat u_sky_color, create a gradient: darker at horizon, lighter at zenith.
    vec3 reflect_dir = reflect(-view_dir, n);
    float sky_y = clamp(reflect_dir.z * 0.5 + 0.5, 0.0, 1.0); // Z is up
    vec3 horizon_color = u_sky_color * 0.4;
    vec3 zenith_color = u_sky_color * 1.2;
    vec3 reflection = mix(horizon_color, zenith_color, pow(sky_y, 0.5));

    // ---- 5. Rim lighting for edge definition ----
    float rim = pow(1.0 - ndv, 3.0) * 0.15;
    vec3 rim_color = u_sky_color * rim;

    // ---- Combine ----
    vec3 color = mix(refracted, reflection, fresnel) + specular + sss + rim_color;
    frag_color = vec4(tonemap_hdr(color, u_exposure), 1.0);
}
