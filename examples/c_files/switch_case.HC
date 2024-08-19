I32 switch_case_test(I32 i){
	switch (i){
		case 0: return -1;
		case 1 ... 10: return 1;
	}
	return 0;
}
