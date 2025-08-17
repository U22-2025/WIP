#include "wiplib/utils/auth.hpp"
#include "wiplib/packet/packet.hpp"
#include <random>
#include <sstream>
#include <iostream>

namespace wiplib::utils {

namespace {
// Minimal SHA-256 implementation
struct SHA256 {
    uint32_t state[8];
    uint64_t bitlen;
    uint8_t data[64];
    size_t datalen;

    static inline uint32_t rotr(uint32_t x, uint32_t n){ return (x>>n) | (x<<(32-n)); }
    static inline uint32_t ch(uint32_t x,uint32_t y,uint32_t z){ return (x & y) ^ (~x & z); }
    static inline uint32_t maj(uint32_t x,uint32_t y,uint32_t z){ return (x & y) ^ (x & z) ^ (y & z); }
    static inline uint32_t bsig0(uint32_t x){ return rotr(x,2) ^ rotr(x,13) ^ rotr(x,22); }
    static inline uint32_t bsig1(uint32_t x){ return rotr(x,6) ^ rotr(x,11) ^ rotr(x,25); }
    static inline uint32_t ssig0(uint32_t x){ return rotr(x,7) ^ rotr(x,18) ^ (x>>3); }
    static inline uint32_t ssig1(uint32_t x){ return rotr(x,17) ^ rotr(x,19) ^ (x>>10); }

    void init(){
        state[0]=0x6a09e667u; state[1]=0xbb67ae85u; state[2]=0x3c6ef372u; state[3]=0xa54ff53au;
        state[4]=0x510e527fu; state[5]=0x9b05688cu; state[6]=0x1f83d9abu; state[7]=0x5be0cd19u;
        bitlen=0; datalen=0;
    }

    void transform(const uint8_t block[64]){
        static const uint32_t K[64]={
            0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
            0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
            0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
            0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
            0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
            0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
            0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
            0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
        uint32_t m[64];
        for (int i=0;i<16;++i){ m[i] = (uint32_t)block[i*4]<<24 | (uint32_t)block[i*4+1]<<16 | (uint32_t)block[i*4+2]<<8 | (uint32_t)block[i*4+3]; }
        for (int i=16;i<64;++i){ m[i] = ssig1(m[i-2]) + m[i-7] + ssig0(m[i-15]) + m[i-16]; }
        uint32_t a=state[0],b=state[1],c=state[2],d=state[3],e=state[4],f=state[5],g=state[6],h=state[7];
        for(int i=0;i<64;++i){ uint32_t t1=h + bsig1(e) + ch(e,f,g) + K[i] + m[i]; uint32_t t2 = bsig0(a) + maj(a,b,c); h=g; g=f; f=e; e=d + t1; d=c; c=b; b=a; a=t1 + t2; }
        state[0]+=a; state[1]+=b; state[2]+=c; state[3]+=d; state[4]+=e; state[5]+=f; state[6]+=g; state[7]+=h;
    }

    void update(const uint8_t* data_in, size_t len){
        for(size_t i=0;i<len;++i){ data[datalen++] = data_in[i]; if (datalen==64){ transform(data); bitlen += 512; datalen=0; } }
    }

    void final(uint8_t out[32]){
        uint64_t bitlen_total = bitlen + datalen*8;
        // append '1' bit
        data[datalen++] = 0x80;
        if (datalen > 56){ while(datalen<64) data[datalen++] = 0x00; transform(data); datalen=0; }
        while(datalen<56) data[datalen++] = 0x00;
        // append length big-endian
        for (int i=7;i>=0;--i){ data[datalen++] = (uint8_t)((bitlen_total >> (i*8)) & 0xFF); }
        transform(data);
        for (int i=0;i<8;++i){ out[i*4+0] = (uint8_t)((state[i] >> 24) & 0xFF); out[i*4+1] = (uint8_t)((state[i] >> 16) & 0xFF); out[i*4+2] = (uint8_t)((state[i] >> 8) & 0xFF); out[i*4+3] = (uint8_t)(state[i] & 0xFF); }
    }
};
}

WIPAuth::WIPAuth(const SecurityPolicy& policy) : policy_(policy) {}
WIPAuth::~WIPAuth() = default;

AuthResult WIPAuth::authenticate_with_passphrase(const std::string& passphrase, const std::string& user_id) {
    increment_stat("auth_attempts");
    // Simple: accept if passphrase previously set via set_passphrase
    for (auto& kv : passphrases_) {
        if (kv.first == passphrase) {
            AuthResult r; r.success = true; r.level = AuthLevel::Standard; r.token = generate_token(); r.expires_in = policy_.token_lifetime;
            TokenInfo ti{r.token, user_id, r.level, std::chrono::steady_clock::now(), policy_.token_lifetime, {}, true};
            std::lock_guard<std::mutex> lk(tokens_mutex_); active_tokens_[r.token] = ti; return r;
        }
    }
    return {false, "", std::chrono::seconds{0}, AuthLevel::None, "invalid passphrase", {}};
}

AuthResult WIPAuth::authenticate_with_token(const std::string& token) {
    std::lock_guard<std::mutex> lk(tokens_mutex_);
    auto it = active_tokens_.find(token);
    if (it != active_tokens_.end() && it->second.is_valid()) {
        return {true, token, it->second.remaining_time(), it->second.level, "", {}};
    }
    return {false, token, std::chrono::seconds{0}, AuthLevel::None, "invalid token", {}};
}

AuthResult WIPAuth::authenticate_with_api_key(const std::string& api_key, const std::string&) {
    auto it = api_keys_.find(api_key);
    if (it != api_keys_.end()) {
        AuthResult r; r.success = true; r.level = AuthLevel::Standard; r.token = generate_token(); r.expires_in = policy_.token_lifetime;
        std::lock_guard<std::mutex> lk(tokens_mutex_); active_tokens_[r.token] = TokenInfo{r.token, "", r.level, std::chrono::steady_clock::now(), policy_.token_lifetime, {}, true};
        return r;
    }
    return {false, "", std::chrono::seconds{0}, AuthLevel::None, "invalid api key", {}};
}

AuthResult WIPAuth::authenticate_with_certificate(const std::string&, const std::string&) { return {false, "", std::chrono::seconds{0}, AuthLevel::None, "not implemented", {}}; }

AuthResult WIPAuth::refresh_token(const std::string& old_token) {
    auto v = validate_token(old_token);
    if (!v) return {false, old_token, std::chrono::seconds{0}, AuthLevel::None, "invalid", {}};
    auto r = authenticate_with_token(old_token);
    return r;
}

bool WIPAuth::invalidate_token(const std::string& token) { std::lock_guard<std::mutex> lk(tokens_mutex_); return active_tokens_.erase(token) > 0; }
size_t WIPAuth::invalidate_all_tokens() { std::lock_guard<std::mutex> lk(tokens_mutex_); size_t n = active_tokens_.size(); active_tokens_.clear(); return n; }

std::optional<TokenInfo> WIPAuth::validate_token(const std::string& token) const { std::lock_guard<std::mutex> lk(tokens_mutex_); auto it = active_tokens_.find(token); if (it!=active_tokens_.end() && it->second.is_valid()) return it->second; return std::nullopt; }
AuthLevel WIPAuth::get_user_auth_level(const std::string&) const { return AuthLevel::Standard; }
bool WIPAuth::check_auth_level(AuthLevel required, const std::string& token) const { auto ti = validate_token(token); return ti && static_cast<int>(ti->level) >= static_cast<int>(required); }
void WIPAuth::set_passphrase(const std::string& passphrase, AuthLevel) { passphrases_[passphrase] = passphrase; }
void WIPAuth::set_api_key(const std::string& api_key, const std::string& secret_key, AuthLevel) { api_keys_[api_key] = {secret_key, ""}; }
void WIPAuth::add_user(const std::string& user_id, const std::string& credentials, AuthLevel level) { users_[user_id] = UserInfo{user_id, credentials, level}; }
bool WIPAuth::remove_user(const std::string& user_id) { return users_.erase(user_id) > 0; }
void WIPAuth::update_security_policy(const SecurityPolicy& p) { policy_ = p; }
SecurityPolicy WIPAuth::get_security_policy() const { return policy_; }
bool WIPAuth::is_host_allowed(const std::string&) const { return true; }
std::unordered_map<std::string, uint64_t> WIPAuth::get_auth_statistics() const { return {}; }
size_t WIPAuth::get_active_token_count() const { std::lock_guard<std::mutex> lk(tokens_mutex_); return active_tokens_.size(); }
size_t WIPAuth::cleanup_expired_tokens() { std::lock_guard<std::mutex> lk(tokens_mutex_); size_t removed=0; for (auto it=active_tokens_.begin(); it!=active_tokens_.end();) { if (!it->second.is_valid()) { it = active_tokens_.erase(it); removed++; } else ++it; } return removed; }
void WIPAuth::set_audit_logging_enabled(bool) {}
void WIPAuth::set_debug_enabled(bool) {}

std::string WIPAuth::generate_token() { static std::mt19937 rng{std::random_device{}()}; std::ostringstream ss; for (int i=0;i<16;++i) ss << std::hex << (rng() & 0xFF); return ss.str(); }
std::string WIPAuth::hash_string(const std::string& input) const { return input; }
bool WIPAuth::verify_hash(const std::string& input, const std::string& hash) const { return input == hash; }
bool WIPAuth::is_user_locked(const std::string&) const { return false; }
void WIPAuth::record_failed_attempt(const std::string&) {}
void WIPAuth::reset_failed_attempts(const std::string&) {}
void WIPAuth::log_auth_event(const std::string&, const std::string&, bool) const {}
void WIPAuth::log_debug(const std::string&) const {}
void WIPAuth::increment_stat(const std::string&) {}
AuthLevel WIPAuth::string_to_auth_level(const std::string&) const { return AuthLevel::Standard; }
std::string WIPAuth::auth_level_to_string(AuthLevel) const { return "standard"; }
bool WIPAuth::is_token_near_expiry(const TokenInfo&) const { return false; }

// crypto implementations
namespace crypto {
// --- SHA1 ---
struct SHA1 {
    uint32_t h0,h1,h2,h3,h4; uint64_t bitlen; uint8_t data[64]; size_t datalen;
    static inline uint32_t rol(uint32_t x, uint32_t n){ return (x<<n) | (x>>(32-n)); }
    void init(){ h0=0x67452301u; h1=0xEFCDAB89u; h2=0x98BADCFEu; h3=0x10325476u; h4=0xC3D2E1F0u; bitlen=0; datalen=0; }
    void transform(const uint8_t block[64]){
        uint32_t w[80]; for (int i=0;i<16;++i){ w[i] = (uint32_t)block[i*4]<<24 | (uint32_t)block[i*4+1]<<16 | (uint32_t)block[i*4+2]<<8 | (uint32_t)block[i*4+3]; }
        for (int i=16;i<80;++i) w[i] = rol(w[i-3] ^ w[i-8] ^ w[i-14] ^ w[i-16], 1);
        uint32_t a=h0,b=h1,c=h2,d=h3,e=h4,f,k,temp;
        for (int i=0;i<80;++i){ if (i<20){ f=(b & c) | ((~b) & d); k=0x5A827999; } else if (i<40){ f=b ^ c ^ d; k=0x6ED9EBA1; } else if (i<60){ f=(b & c) | (b & d) | (c & d); k=0x8F1BBCDC; } else { f=b ^ c ^ d; k=0xCA62C1D6; } temp = rol(a,5) + f + e + k + w[i]; e=d; d=c; c=rol(b,30); b=a; a=temp; }
        h0 += a; h1 += b; h2 += c; h3 += d; h4 += e;
    }
    void update(const uint8_t* data_in, size_t len){ for (size_t i=0;i<len;++i){ data[datalen++] = data_in[i]; if (datalen==64){ transform(data); bitlen += 512; datalen=0; } } }
    void final(uint8_t out[20]){ uint64_t bitlen_total = bitlen + datalen*8; data[datalen++] = 0x80; if (datalen>56){ while(datalen<64) data[datalen++]=0; transform(data); datalen=0;} while(datalen<56) data[datalen++]=0; for (int i=7;i>=0;--i) data[datalen++] = (uint8_t)((bitlen_total>>(i*8))&0xFF); transform(data); uint32_t h[5]={h0,h1,h2,h3,h4}; for (int i=0;i<5;++i){ out[i*4+0]=(uint8_t)((h[i]>>24)&0xFF); out[i*4+1]=(uint8_t)((h[i]>>16)&0xFF); out[i*4+2]=(uint8_t)((h[i]>>8)&0xFF); out[i*4+3]=(uint8_t)(h[i]&0xFF);} }
};

std::vector<uint8_t> sha1_bytes(const std::vector<uint8_t>& data){ SHA1 ctx; ctx.init(); if (!data.empty()) ctx.update(data.data(), data.size()); uint8_t out[20]; ctx.final(out); return std::vector<uint8_t>(out,out+20); }

// --- MD5 ---
struct MD5 {
    uint32_t a,b,c,d; uint64_t bitlen; uint8_t data[64]; size_t datalen;
    static inline uint32_t F(uint32_t x,uint32_t y,uint32_t z){ return (x & y) | (~x & z);} static inline uint32_t G(uint32_t x,uint32_t y,uint32_t z){ return (x & z) | (y & ~z);} static inline uint32_t H(uint32_t x,uint32_t y,uint32_t z){ return x ^ y ^ z;} static inline uint32_t I(uint32_t x,uint32_t y,uint32_t z){ return y ^ (x | ~z);} static inline uint32_t rotl(uint32_t x,uint32_t n){ return (x<<n) | (x>>(32-n)); }
    void init(){ a=0x67452301u; b=0xEFCDAB89u; c=0x98BADCFEu; d=0x10325476u; bitlen=0; datalen=0; }
    void transform(const uint8_t block[64]){
        uint32_t X[16]; for (int i=0;i<16;++i){ X[i] = (uint32_t)block[i*4] | ((uint32_t)block[i*4+1]<<8) | ((uint32_t)block[i*4+2]<<16) | ((uint32_t)block[i*4+3]<<24); }
        uint32_t AA=a,BB=b,CC=c,DD=d;
        auto OP=[&](auto f,uint32_t& a,uint32_t b,uint32_t c,uint32_t d,uint32_t x,uint32_t s,uint32_t ac){ a = a + f(b,c,d) + x + ac; a = rotl(a, s) + b; };
        // Round 1
        OP(F,a,b,c,d,X[0],7,0xd76aa478); OP(F,d,a,b,c,X[1],12,0xe8c7b756); OP(F,c,d,a,b,X[2],17,0x242070db); OP(F,b,c,d,a,X[3],22,0xc1bdceee);
        OP(F,a,b,c,d,X[4],7,0xf57c0faf); OP(F,d,a,b,c,X[5],12,0x4787c62a); OP(F,c,d,a,b,X[6],17,0xa8304613); OP(F,b,c,d,a,X[7],22,0xfd469501);
        OP(F,a,b,c,d,X[8],7,0x698098d8); OP(F,d,a,b,c,X[9],12,0x8b44f7af); OP(F,c,d,a,b,X[10],17,0xffff5bb1); OP(F,b,c,d,a,X[11],22,0x895cd7be);
        OP(F,a,b,c,d,X[12],7,0x6b901122); OP(F,d,a,b,c,X[13],12,0xfd987193); OP(F,c,d,a,b,X[14],17,0xa679438e); OP(F,b,c,d,a,X[15],22,0x49b40821);
        // Round 2
        OP(G,a,b,c,d,X[1],5,0xf61e2562); OP(G,d,a,b,c,X[6],9,0xc040b340); OP(G,c,d,a,b,X[11],14,0x265e5a51); OP(G,b,c,d,a,X[0],20,0xe9b6c7aa);
        OP(G,a,b,c,d,X[5],5,0xd62f105d); OP(G,d,a,b,c,X[10],9,0x02441453); OP(G,c,d,a,b,X[15],14,0xd8a1e681); OP(G,b,c,d,a,X[4],20,0xe7d3fbc8);
        OP(G,a,b,c,d,X[9],5,0x21e1cde6); OP(G,d,a,b,c,X[14],9,0xc33707d6); OP(G,c,d,a,b,X[3],14,0xf4d50d87); OP(G,b,c,d,a,X[8],20,0x455a14ed);
        OP(G,a,b,c,d,X[13],5,0xa9e3e905); OP(G,d,a,b,c,X[2],9,0xfcefa3f8); OP(G,c,d,a,b,X[7],14,0x676f02d9); OP(G,b,c,d,a,X[12],20,0x8d2a4c8a);
        // Round 3
        OP(H,a,b,c,d,X[5],4,0xfffa3942); OP(H,d,a,b,c,X[8],11,0x8771f681); OP(H,c,d,a,b,X[11],16,0x6d9d6122); OP(H,b,c,d,a,X[14],23,0xfde5380c);
        OP(H,a,b,c,d,X[1],4,0xa4beea44); OP(H,d,a,b,c,X[4],11,0x4bdecfa9); OP(H,c,d,a,b,X[7],16,0xf6bb4b60); OP(H,b,c,d,a,X[10],23,0xbebfbc70);
        OP(H,a,b,c,d,X[13],4,0x289b7ec6); OP(H,d,a,b,c,X[0],11,0xeaa127fa); OP(H,c,d,a,b,X[3],16,0xd4ef3085); OP(H,b,c,d,a,X[6],23,0x04881d05);
        // Round 4
        OP(I,a,b,c,d,X[0],6,0xf4292244); OP(I,d,a,b,c,X[7],10,0x432aff97); OP(I,c,d,a,b,X[14],15,0xab9423a7); OP(I,b,c,d,a,X[5],21,0xfc93a039);
        OP(I,a,b,c,d,X[12],6,0x655b59c3); OP(I,d,a,b,c,X[3],10,0x8f0ccc92); OP(I,c,d,a,b,X[10],15,0xffeff47d); OP(I,b,c,d,a,X[1],21,0x85845dd1);
        OP(I,a,b,c,d,X[8],6,0x6fa87e4f); OP(I,d,a,b,c,X[15],10,0xfe2ce6e0); OP(I,c,d,a,b,X[6],15,0xa3014314); OP(I,b,c,d,a,X[13],21,0x4e0811a1);
        a += AA; b += BB; c += CC; d += DD;
    }
    void update(const uint8_t* data_in, size_t len){ for(size_t i=0;i<len;++i){ data[datalen++] = data_in[i]; if (datalen==64){ transform(data); bitlen += 512; datalen=0; } } }
    void final(uint8_t out[16]){ uint64_t bitlen_total = bitlen + datalen*8; data[datalen++] = 0x80; while (datalen%64 != 56) data[datalen++]=0x00; for (int i=0;i<8;++i) data[datalen++] = (uint8_t)((bitlen_total >> (8*i)) & 0xFF); transform(data); auto wr=[&](uint32_t v,int idx){ out[idx] = (uint8_t)(v & 0xFF); out[idx+1]=(uint8_t)((v>>8)&0xFF); out[idx+2]=(uint8_t)((v>>16)&0xFF); out[idx+3]=(uint8_t)((v>>24)&0xFF); }; wr(a,0); wr(b,4); wr(c,8); wr(d,12); }
};

std::vector<uint8_t> md5_bytes(const std::vector<uint8_t>& data){ MD5 ctx; ctx.init(); if (!data.empty()) ctx.update(data.data(), data.size()); uint8_t out[16]; ctx.final(out); return std::vector<uint8_t>(out,out+16); }

// HMAC for SHA1 and MD5 reuse same block size 64
static std::vector<uint8_t> hmac_bytes(const std::vector<uint8_t>& key, const std::vector<uint8_t>& msg, std::function<std::vector<uint8_t>(const std::vector<uint8_t>&)> hash_fn, size_t out_size){
    const size_t block=64; std::vector<uint8_t> k=key; if (k.size()>block) k = hash_fn(k); if (k.size()<block) k.resize(block,0x00); std::vector<uint8_t> o(block), i(block); for (size_t n=0;n<block;++n){ o[n]=k[n]^0x5c; i[n]=k[n]^0x36; }
    std::vector<uint8_t> inner; inner.reserve(block+msg.size()); inner.insert(inner.end(), i.begin(), i.end()); inner.insert(inner.end(), msg.begin(), msg.end()); auto inner_hash = hash_fn(inner);
    std::vector<uint8_t> outer; outer.reserve(block+inner_hash.size()); outer.insert(outer.end(), o.begin(), o.end()); outer.insert(outer.end(), inner_hash.begin(), inner_hash.end()); auto out = hash_fn(outer); if (out.size()>out_size) out.resize(out_size); return out;
}

std::vector<uint8_t> hmac_sha1_bytes(const std::vector<uint8_t>& key, const std::vector<uint8_t>& message){ return hmac_bytes(key, message, sha1_bytes, 20); }
std::vector<uint8_t> hmac_md5_bytes(const std::vector<uint8_t>& key, const std::vector<uint8_t>& message){ return hmac_bytes(key, message, md5_bytes, 16); }
std::vector<uint8_t> sha256_bytes(const std::vector<uint8_t>& data){
    SHA256 ctx; ctx.init(); if (!data.empty()) ctx.update(data.data(), data.size()); uint8_t out[32]; ctx.final(out); return std::vector<uint8_t>(out, out+32);
}
std::string sha256(const std::string& input){ auto d = std::vector<uint8_t>(input.begin(), input.end()); auto out = sha256_bytes(d); static const char* hex="0123456789abcdef"; std::string s; s.resize(64); for (size_t i=0;i<32;++i){ s[i*2]=hex[(out[i]>>4)&0xF]; s[i*2+1]=hex[out[i]&0xF]; } return s; }
std::vector<uint8_t> hmac_sha256_bytes(const std::vector<uint8_t>& key, const std::vector<uint8_t>& message){
    const size_t block_size = 64;
    std::vector<uint8_t> k = key;
    if (k.size() > block_size) { k = sha256_bytes(k); }
    if (k.size() < block_size) k.resize(block_size, 0x00);
    std::vector<uint8_t> o_key(block_size), i_key(block_size);
    for (size_t i=0;i<block_size;++i){ o_key[i] = k[i] ^ 0x5c; i_key[i] = k[i] ^ 0x36; }
    // inner = H(i_key || message)
    std::vector<uint8_t> inner_input; inner_input.reserve(block_size + message.size()); inner_input.insert(inner_input.end(), i_key.begin(), i_key.end()); inner_input.insert(inner_input.end(), message.begin(), message.end());
    auto inner = sha256_bytes(inner_input);
    // outer = H(o_key || inner)
    std::vector<uint8_t> outer_input; outer_input.reserve(block_size + inner.size()); outer_input.insert(outer_input.end(), o_key.begin(), o_key.end()); outer_input.insert(outer_input.end(), inner.begin(), inner.end());
    return sha256_bytes(outer_input);
}
std::string hmac_sha256(const std::string& key, const std::string& message){ auto k = std::vector<uint8_t>(key.begin(), key.end()); auto m = std::vector<uint8_t>(message.begin(), message.end()); auto out = hmac_sha256_bytes(k, m); static const char* hex="0123456789abcdef"; std::string s(64,'0'); for (size_t i=0;i<32;++i){ s[i*2]=hex[(out[i]>>4)&0xF]; s[i*2+1]=hex[out[i]&0xF]; } return s; }
std::string generate_salt(size_t length) { return std::string(length, 's'); }
std::string pbkdf2_hash(const std::string& password, const std::string& salt, int) { return sha256(password+salt); }
std::string aes_encrypt(const std::string& plaintext, const std::string&) { return plaintext; }
std::string aes_decrypt(const std::string& ciphertext, const std::string&) { return ciphertext; }
std::string base64_encode(const std::vector<uint8_t>&) { return ""; }
std::vector<uint8_t> base64_decode(const std::string&) { return {}; }
} // namespace crypto

// Python-compatible auth hash helpers
std::vector<uint8_t> WIPAuth::calculate_auth_hash(uint16_t packet_id, uint64_t timestamp, const std::string& passphrase, HashAlgorithm algo) {
    // message: f"{packet_id}:{timestamp}:{passphrase}" encoded utf-8; key = passphrase utf-8
    std::string msg = std::to_string(static_cast<unsigned>(packet_id & 0x0FFFu)) + ":" + std::to_string(timestamp) + ":" + passphrase;
    std::vector<uint8_t> key(passphrase.begin(), passphrase.end());
    std::vector<uint8_t> m(msg.begin(), msg.end());
    switch (algo) {
        case HashAlgorithm::MD5:   return crypto::hmac_md5_bytes(key, m);
        case HashAlgorithm::SHA1:  return crypto::hmac_sha1_bytes(key, m);
        case HashAlgorithm::SHA256:
        default:                   return crypto::hmac_sha256_bytes(key, m);
    }
}

static bool consttime_equal(const std::vector<uint8_t>& a, const std::vector<uint8_t>& b){ if (a.size()!=b.size()) return false; uint8_t acc=0; for (size_t i=0;i<a.size();++i) acc |= (a[i]^b[i]); return acc==0; }

bool WIPAuth::verify_auth_hash(uint16_t packet_id, uint64_t timestamp, const std::string& passphrase, const std::vector<uint8_t>& received_hash, HashAlgorithm algo) {
    auto expected = calculate_auth_hash(packet_id, timestamp, passphrase, algo);
    return consttime_equal(expected, received_hash);
}

// Overloads using string algorithm name
std::vector<uint8_t> WIPAuth::calculate_auth_hash(uint16_t packet_id, uint64_t timestamp, const std::string& passphrase, const std::string& algo_name){
    return calculate_auth_hash(packet_id, timestamp, passphrase, parse_hash_algorithm(algo_name));
}

bool WIPAuth::verify_auth_hash(uint16_t packet_id, uint64_t timestamp, const std::string& passphrase, const std::vector<uint8_t>& received_hash, const std::string& algo_name){
    return verify_auth_hash(packet_id, timestamp, passphrase, received_hash, parse_hash_algorithm(algo_name));
}

wiplib::utils::HashAlgorithm WIPAuth::parse_hash_algorithm(const std::string& name){
    std::string n; n.reserve(name.size());
    for (char c : name) n.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(c))));
    if (n == "md5") return HashAlgorithm::MD5;
    if (n == "sha1") return HashAlgorithm::SHA1;
    return HashAlgorithm::SHA256;
}

wiplib::utils::HashAlgorithm WIPAuth::get_default_hash_algorithm_from_env(){
    const char* p = std::getenv("WIP_AUTH_ALGO");
    if (!p) return HashAlgorithm::SHA256;
    return parse_hash_algorithm(p);
}

// Factory
std::unique_ptr<WIPAuth> AuthFactory::create_basic_auth() { return std::make_unique<WIPAuth>(); }
std::unique_ptr<WIPAuth> AuthFactory::create_high_security_auth() { SecurityPolicy p; p.minimum_auth_level = AuthLevel::Advanced; return std::make_unique<WIPAuth>(p); }
std::unique_ptr<WIPAuth> AuthFactory::create_development_auth() { SecurityPolicy p; p.require_token_renewal = false; return std::make_unique<WIPAuth>(p); }
std::unique_ptr<WIPAuth> AuthFactory::create_custom_auth(const SecurityPolicy& p) { return std::make_unique<WIPAuth>(p); }

} // namespace wiplib::utils

// Phase 1 helper: attach Python-compatible auth_hash extended field
namespace wiplib::utils {

static inline std::string to_hex_lower(const std::vector<uint8_t>& bytes){
    static const char* hex = "0123456789abcdef";
    std::string out;
    out.resize(bytes.size()*2);
    for (size_t i=0;i<bytes.size();++i){
        out[i*2] = hex[(bytes[i] >> 4) & 0xF];
        out[i*2+1] = hex[bytes[i] & 0xF];
    }
    return out;
}

bool WIPAuth::attach_auth_hash(wiplib::proto::Packet& packet, const std::string& passphrase){
    if (passphrase.empty()) {
        std::cerr << "DEBUG: WIPAuth::attach_auth_hash - passphrase is empty" << std::endl;
        return false;
    }
    std::cerr << "DEBUG: WIPAuth::attach_auth_hash called with passphrase: " << passphrase << std::endl;
    std::cerr << "DEBUG: packet_id: " << packet.header.packet_id << ", timestamp: " << packet.header.timestamp << std::endl;
    
    // packet_id は 12bit 値だが、ヘッダへの格納値をそのまま使用（Python 実装互換）
    auto mac = calculate_auth_hash(packet.header.packet_id, packet.header.timestamp, passphrase, HashAlgorithm::SHA256);
    auto hex = to_hex_lower(mac);
    std::cerr << "DEBUG: generated hash: " << hex << std::endl;
    
    wiplib::proto::ExtendedField f{};
    // Python の extended_fields.json で auth_hash は id=4, type=str
    f.data_type = 4; // auth_hash
    f.data.assign(hex.begin(), hex.end());
    packet.extensions.push_back(std::move(f));
    packet.header.flags.extended = true;
    packet.header.flags.auth_enabled = true; // リクエスト側の被認証フラグ
    
    std::cerr << "DEBUG: Extension added, total extensions: " << packet.extensions.size() << std::endl;
    std::cerr << "DEBUG: flags.extended: " << packet.header.flags.extended << ", flags.auth_enabled: " << packet.header.flags.auth_enabled << std::endl;
    return true;
}

} // namespace wiplib::utils
