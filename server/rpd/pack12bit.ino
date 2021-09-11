void Pack12bit::push(unsigned short v)
{
  if(t)
  {
    unsigned short rs = (t - 1) << 2; // right shift

    on_produce((ov >> rs) | (v << (12 - rs)));
  }

  t = (t + 1) & 3;
  ov = v;
}

/*void Pack12bit::finalize()
{
  if(t != 3)
  {
    push(0);
  }
}*/

void Pack12bit::reset()
{
    t = 0;
}

void Pack12bit::onProduce(CallbackFunction f)
{
    on_produce = f;
}
