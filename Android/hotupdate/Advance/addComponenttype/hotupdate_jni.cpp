/*
 * Copyright (C) 2024 The Vendor Project
 * SPDX-License-Identifier: Apache-2.0
 *
 * JNI 桥接层：只做类型转换，不含任何业务逻辑。
 * componentType 仅作透传参数交给 native reader，过滤语义由 C++ 侧统一定义。
 *
 * 依赖：native reader 需提供以下签名（新增 componentType）：
 *   std::vector<std::string> gethotupdatefiles(int componentType);
 *   std::vector<std::string> gethotupdateprops(int componentType);
 *   char* GetHotUpdateFile(const char* pathSuffix, int type,
 *                          int componentType, char* buf, int bufLen);
 */

#define LOG_TAG "hotupdate_jni"

#include <jni.h>
#include <limits.h>          // PATH_MAX

#include <string>
#include <vector>

#include <log/log.h>

#include "hotupdate/hotupdate_client.h"   // native reader 公开头

namespace {

// vector<string> -> Java String[]；任何分配失败返回 nullptr（Java 侧按空处理）
jobjectArray VectorToStringArray(JNIEnv* env,
                                 const std::vector<std::string>& items) {
    jclass string_class = env->FindClass("java/lang/String");
    if (string_class == nullptr) {
        return nullptr;  // 有 pending 异常
    }
    jobjectArray array =
        env->NewObjectArray(static_cast<jsize>(items.size()), string_class, nullptr);
    env->DeleteLocalRef(string_class);
    if (array == nullptr) {
        return nullptr;  // OOM，pending 异常
    }
    jsize index = 0;
    for (const std::string& item : items) {
        jstring str = env->NewStringUTF(item.c_str());
        if (str == nullptr) {
            return nullptr;  // OOM
        }
        env->SetObjectArrayElement(array, index++, str);
        // 及时释放局部引用，避免记录数较多时局部引用表溢出
        env->DeleteLocalRef(str);
    }
    return array;
}

jobjectArray nativeGetHotUpdateFiles(JNIEnv* env, jclass /*clazz*/,
                                     jint component_type) {
    return VectorToStringArray(
        env, android::hotupdate::gethotupdatefiles(static_cast<int>(component_type)));
}

jobjectArray nativeGetHotUpdateProps(JNIEnv* env, jclass /*clazz*/,
                                     jint component_type) {
    return VectorToStringArray(
        env, android::hotupdate::gethotupdateprops(static_cast<int>(component_type)));
}

jstring nativeGetHotUpdateFile(JNIEnv* env, jclass /*clazz*/,
                               jstring j_suffix, jint type, jint component_type) {
    if (j_suffix == nullptr) {
        return nullptr;
    }
    const char* suffix = env->GetStringUTFChars(j_suffix, nullptr);
    if (suffix == nullptr) {
        return nullptr;  // OOM
    }

    // buf/bufLen 在此消化：栈上缓冲区，交给 C++ 填充绝对路径
    char buf[PATH_MAX];
    char* result = android::hotupdate::GetHotUpdateFile(
        suffix, static_cast<int>(type), static_cast<int>(component_type),
        buf, static_cast<int>(sizeof(buf)));

    env->ReleaseStringUTFChars(j_suffix, suffix);

    return result == nullptr ? nullptr : env->NewStringUTF(result);
}

// 方法描述符已同步 componentType：
//   nativeGetHotUpdateFiles / Props : (I)[Ljava/lang/String;
//   nativeGetHotUpdateFile          : (Ljava/lang/String;II)Ljava/lang/String;
const JNINativeMethod kMethods[] = {
    {"nativeGetHotUpdateFiles", "(I)[Ljava/lang/String;",
     reinterpret_cast<void*>(nativeGetHotUpdateFiles)},
    {"nativeGetHotUpdateProps", "(I)[Ljava/lang/String;",
     reinterpret_cast<void*>(nativeGetHotUpdateProps)},
    {"nativeGetHotUpdateFile", "(Ljava/lang/String;II)Ljava/lang/String;",
     reinterpret_cast<void*>(nativeGetHotUpdateFile)},
};

const char* kClassName = "com/vendor/hotupdate/HotUpdateManager";

}  // namespace

// RegisterNatives 绑定：对外只导出 JNI_OnLoad 一个符号，桥接函数保持匿名命名空间（不导出）
extern "C" JNIEXPORT jint JNI_OnLoad(JavaVM* vm, void* /*reserved*/) {
    JNIEnv* env = nullptr;
    if (vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK) {
        ALOGE("GetEnv failed");
        return JNI_ERR;
    }
    jclass clazz = env->FindClass(kClassName);
    if (clazz == nullptr) {
        ALOGE("FindClass %s failed", kClassName);
        return JNI_ERR;
    }
    jint rc = env->RegisterNatives(
        clazz, kMethods, sizeof(kMethods) / sizeof(kMethods[0]));
    env->DeleteLocalRef(clazz);
    if (rc != JNI_OK) {
        ALOGE("RegisterNatives failed: %d", rc);
        return JNI_ERR;
    }
    return JNI_VERSION_1_6;
}
