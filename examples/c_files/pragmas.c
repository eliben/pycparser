int i;

#pragma joe

int main() {
  int a = 1;
#pragma inmain

  for (int i = 0; i < 3; i++) {
#pragma infor
    a += i;
  }

  return a;
}
