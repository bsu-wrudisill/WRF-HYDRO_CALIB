module test
contains
subroutine readnc(FILE_NAME, featureid, n, outputfile)
  use netcdf
  implicit none 
  character (len = *) :: FILE_NAME
  character (len = *) :: outputfile
  character (len = *), parameter :: varname = "streamflow"
  integer :: featureid, n, ncid, varid, status
  real :: data(n), output(1)
  
  !f2py intent(out) output
  
  ! open the file 
  status = nf90_open(FILE_NAME, NF90_NOWRITE, ncid)
  
  !! get the variable 
  status = nf90_inq_varid(ncid, varname, varid)
  
  !! get the data 
  status = nf90_get_var(ncid, varid, data)
  
  !! now we can access the data ... i think
  output = data(featureid)
 
  ! write the data to a text file 
  open (10, file=outputfile, status='unknown', position='append')
  write(10, *) FILE_NAME, ',', output
  close(10)
  
  ! close the netcdf file  
  status = nf90_close(ncid)
  
end subroutine readnc
end module test 
