#include <stdio.h>
#include <stdlib.h>
#include <stdnoreturn.h>
#include <threads.h>
#include <assert.h>
#include <stdatomic.h>
#include <stdalign.h>
#include <wchar.h>

/* C11 thread locals */
_Thread_local int flag;
thread_local int flag2;
_Atomic int flag3;
_Atomic(int) flag4;
_Atomic(_Atomic(int) *) flag5;
atomic_bool flag6;
_Alignas(32) int q32;
_Alignas(long long) int qll;
alignas(64) int qqq;

static_assert(sizeof(flag) == sizeof(flag2), "Really unexpected size difference");

noreturn void func2(void)
{
  abort();
}

_Noreturn void func(void)
{
  func2();
}

int main()
{
  _Static_assert(sizeof(flag) == sizeof(flag2), "Unexpected size difference");
  _Static_assert(sizeof(flag) == sizeof(flag2));
  static_assert(sizeof(flag) == sizeof(flag2), "Unexpected size difference");
  static_assert(sizeof(flag) == sizeof(flag3), "Unexpected size difference");
  static_assert(sizeof(flag) == sizeof(flag4), "Unexpected size difference");
  static_assert(_Alignof(int) == sizeof(int), "Unexpected int alignment");
  static_assert(alignof(int) == sizeof(int), "Unexpected int alignment");

  wchar_t *w = L"12345";
  char16_t *c16 = u"12345";
  char32_t *c32 = U"12345";
  char *u8 = u8"12345";

  wchar_t wc = L'1';
  char16_t c16c = u'1';
  char32_t c32c = U'1';
  char u8c = u8'1';

  printf("Flag: %d\n", flag);
  printf("Flag2: %d\n", flag2);
  func();
}
