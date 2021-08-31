#include <stdio.h>
#include <stdlib.h>
#include <stdnoreturn.h>
#include <threads.h>
#include <assert.h>

/* C11 thread locals */
_Thread_local int flag;
thread_local int flag2;

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
  static_assert(sizeof(flag) == sizeof(flag2), "Unexpected size difference");

  printf("Flag: %d\n", flag);
  printf("Flag2: %d\n", flag2);
  func();
}
