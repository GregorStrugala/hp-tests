def humidity(self, field, value, error):
    nconv = self._name_converter
    def get_SI_mag(quantity, unit):
        raw_values = self.raw_data[nconv.loc[quantity, 'col_names']].values
        return self.Q_(raw_values).to(unit).magnitude
    Ts = get_SI_mag('Ts', 'K')
    RHs = get_SI_mag('RHs', 'ratio') 
    Tr = get_SI_mag('Tr', 'K')
    RHr = get_SI_mag('RHr', 'ratio')

    ws = psychro('W', 'P', 101325, 'T', Ts, 'RH', RHs)
    wr = psychro('W', 'P', 101325, 'T', Tr, 'RH', RHr)

    if (wr > ws).any():
        error(field, 'The absolute humidity is increasing at least once.')

